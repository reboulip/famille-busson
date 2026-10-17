import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from annuaire.models import Person
from annuaire.views import StaffRequiredMixin
from documents.access import accessible_documents
from photos.access import accessible_albums

from .bulletin_access import accessible_bulletins, user_can_access_bulletin
from .bulletin_import import apply_bulletin_import, stage_bulletin_import
from .bulletin_package import PackageValidationError
from .bulletin_render import build_bulletin_context
from .forms import AttachmentFormSet, BlogPostForm, CommentForm, FormBulletinUpload
from .models import BlogPost, Bulletin, BulletinImport, Comment, Tag


def _authors_initial_json(view):
    """Build the JSON payload used by the person-picker to pre-populate authors."""
    request = view.request
    if request.method == "POST":
        ids = [int(pk) for pk in request.POST.getlist("authors") if pk.isdigit()]
        persons = list(Person.objects.filter(pk__in=ids).order_by("last_name", "first_name"))
    elif getattr(view, "object", None) is not None:
        persons = list(view.object.authors.all().order_by("last_name", "first_name"))
    else:
        profile = getattr(request.user, "profile", None)
        persons = [profile] if profile is not None else []
    return json.dumps([{"id": p.pk, "name": str(p)} for p in persons])


def _documents_initial_json(view):
    """Build the JSON payload used by the document-picker to pre-populate `documents`.

    Scoped to the requesting user's accessible documents, same as the form field
    itself -- a failed-validation redisplay must not leak a restricted document's
    title just because its pk was in the (rejected) POST data."""
    request = view.request
    accessible = accessible_documents(request.user)
    if request.method == "POST":
        ids = [int(pk) for pk in request.POST.getlist("documents") if pk.isdigit()]
        docs = list(accessible.filter(pk__in=ids).order_by("title"))
    elif getattr(view, "object", None) is not None:
        docs = list(view.object.documents.filter(pk__in=accessible).order_by("title"))
    else:
        docs = []
    return json.dumps([{"id": d.pk, "name": d.title} for d in docs])


def _albums_initial_json(view):
    """Build the JSON payload used by the album-picker to pre-populate `albums`.

    Scoped to the requesting user's accessible albums, same as the form field
    itself -- a failed-validation redisplay must not leak a restricted album's
    title just because its pk was in the (rejected) POST data."""
    request = view.request
    accessible = accessible_albums(request.user)
    if request.method == "POST":
        ids = [int(pk) for pk in request.POST.getlist("albums") if pk.isdigit()]
        albums = list(accessible.filter(pk__in=ids).order_by("title"))
    elif getattr(view, "object", None) is not None:
        albums = list(view.object.albums.filter(pk__in=accessible).order_by("title"))
    else:
        albums = []
    return json.dumps([{"id": a.pk, "name": a.title} for a in albums])


class AuthorOrStaffRequiredMixin(LoginRequiredMixin):
    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user
        if user.is_staff:
            return obj
        profile = getattr(user, "profile", None)
        if profile is None or not obj.authors.filter(pk=profile.pk).exists():
            raise PermissionDenied(_("Vous n'êtes pas auteur de cette publication."))
        return obj


class BlogPostListView(LoginRequiredMixin, ListView):
    model = BlogPost
    template_name = "publications/blogpost_list.html"
    context_object_name = "posts"
    paginate_by = 20

    def get_queryset(self):
        qs = BlogPost.objects.prefetch_related("authors", "attachments", "tags").order_by("-created_at")
        tag_id = self.request.GET.get("tag", "")
        if tag_id.isdigit():
            qs = qs.filter(tags__pk=tag_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_tag"] = self.request.GET.get("tag", "")
        context["filter_tags"] = Tag.objects.filter(posts__isnull=False).distinct().order_by("name")
        return context


class BlogPostDetailView(LoginRequiredMixin, DetailView):
    model = BlogPost
    template_name = "publications/blogpost_detail.html"
    context_object_name = "post"

    def _can_edit(self, post):
        user = self.request.user
        if user.is_staff:
            return True
        profile = getattr(user, "profile", None)
        return profile is not None and post.authors.filter(pk=profile.pk).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("comment_form", CommentForm())
        context["can_edit"] = self._can_edit(self.object)
        # is_image/is_pdf are Python properties, not queryset-filterable fields -- group
        # in Python over the already-prefetched attachments rather than issuing 3 queries.
        image_attachments, pdf_attachments, other_attachments = [], [], []
        for attachment in self.object.attachments.all():
            if attachment.is_image:
                image_attachments.append(attachment)
            elif attachment.is_pdf:
                pdf_attachments.append(attachment)
            else:
                other_attachments.append(attachment)
        context["image_attachments"] = image_attachments
        context["pdf_attachments"] = pdf_attachments
        context["other_attachments"] = other_attachments
        # Re-checked at render time, never a stored snapshot: a document later moved
        # into a locked category must silently disappear from the publication page.
        context["linked_documents"] = accessible_documents(self.request.user).filter(publications=self.object)
        # _album_card.html (reused as-is) expects photo_count/cover annotated the same
        # way AlbumListView.get_queryset() does -- without it the card either crashes
        # or silently renders a blank count.
        context["linked_albums"] = (
            accessible_albums(self.request.user)
            .filter(publications=self.object)
            .select_related("cover")
            .annotate(photo_count=Count("photos"))
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        profile = getattr(request.user, "profile", None)
        if profile is None:
            messages.error(request, _("Vous devez compléter votre profil avant de commenter."))
            return redirect("profile-create")
        form = CommentForm(request.POST)
        if form.is_valid():
            Comment.objects.create(
                post=self.object,
                author=profile,
                body=form.cleaned_data["body"],
            )
            return redirect("blogpost-detail", pk=self.object.pk)
        context = self.get_context_data(comment_form=form)
        return self.render_to_response(context)


class BlogPostCreateView(LoginRequiredMixin, CreateView):
    model = BlogPost
    form_class = BlogPostForm
    template_name = "publications/blogpost_form.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not hasattr(request.user, "profile"):
            messages.error(request, _("Vous devez compléter votre profil avant de publier."))
            return redirect("profile-create")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["current_person"] = getattr(self.request.user, "profile", None)
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formsets"] = [AttachmentFormSet(self.request.POST, self.request.FILES)]
        else:
            context["formsets"] = [AttachmentFormSet()]
        context["authors_initial_json"] = _authors_initial_json(self)
        context["documents_initial_json"] = _documents_initial_json(self)
        context["albums_initial_json"] = _albums_initial_json(self)
        context["all_tag_names"] = Tag.objects.values_list("name", flat=True)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        attachment_formset = context["formsets"][0]
        if not attachment_formset.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            profile = getattr(self.request.user, "profile", None)
            if profile is not None and not self.object.authors.filter(pk=profile.pk).exists():
                self.object.authors.add(profile)
            attachment_formset.instance = self.object
            attachment_formset.save()
        return redirect("blogpost-detail", pk=self.object.pk)


class BlogPostUpdateView(AuthorOrStaffRequiredMixin, UpdateView):
    model = BlogPost
    form_class = BlogPostForm
    template_name = "publications/blogpost_form.html"

    def get_form_kwargs(self):
        # Without this, BlogPostForm defaults to user=None -> documents/albums
        # querysets are empty -> the M2M ModelForms validate fine and silently
        # clear every linked document/album on save. See
        # test_blogpost_edit_preserves_linked_documents.
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formsets"] = [
                AttachmentFormSet(self.request.POST, self.request.FILES, instance=self.object),
            ]
        else:
            context["formsets"] = [AttachmentFormSet(instance=self.object)]
        context["authors_initial_json"] = _authors_initial_json(self)
        context["documents_initial_json"] = _documents_initial_json(self)
        context["albums_initial_json"] = _albums_initial_json(self)
        context["all_tag_names"] = Tag.objects.values_list("name", flat=True)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        attachment_formset = context["formsets"][0]
        if not attachment_formset.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            attachment_formset.instance = self.object
            attachment_formset.save()
        return redirect("blogpost-detail", pk=self.object.pk)


class BlogPostDeleteView(AuthorOrStaffRequiredMixin, DeleteView):
    model = BlogPost
    template_name = "publications/blogpost_confirm_delete.html"
    success_url = reverse_lazy("blogpost-list")

    def form_valid(self, form):
        # Soft delete (corbeille, 14.5) -- never .delete() directly here.
        self.object.soft_delete(self.request.user)
        return redirect(self.get_success_url())


class CommentDeleteView(StaffRequiredMixin, DeleteView):
    model = Comment
    template_name = "publications/comment_confirm_delete.html"

    def get_success_url(self):
        return reverse("blogpost-detail", kwargs={"pk": self.object.post.pk})


class BulletinListView(LoginRequiredMixin, ListView):
    model = Bulletin
    template_name = "publications/bulletin_list.html"
    context_object_name = "bulletins"
    paginate_by = 20

    def get_queryset(self):
        return accessible_bulletins(self.request.user).prefetch_related("images").order_by("-sort_date")


class BulletinDetailView(LoginRequiredMixin, DetailView):
    model = Bulletin
    template_name = "publications/bulletin_detail.html"
    context_object_name = "bulletin_obj"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        if not user_can_access_bulletin(self.request.user, obj):
            raise PermissionDenied(_("Vous n'avez pas accès à ce bulletin."))
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        image_urls = {img.image_id: img.file.url for img in self.object.images.all()}
        context.update(build_bulletin_context(self.object.data, image_urls))
        context["source_pdf_url"] = self.object.source_pdf.url if self.object.source_pdf else None
        return context


class BulletinImportUploadView(StaffRequiredMixin, View):
    """Staff-only. Validates the uploaded package and stages it -- nothing is
    written to the published Bulletin/BulletinImage tables here."""

    template_name = "publications/bulletin_import_upload.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {"form": FormBulletinUpload()})

    def post(self, request, *args, **kwargs):
        form = FormBulletinUpload(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        uploaded = form.cleaned_data["package"]
        try:
            bulletin_import = stage_bulletin_import(
                zip_file=uploaded,
                source_pdf=form.cleaned_data.get("source_pdf"),
                uploaded_by=getattr(request.user, "profile", None),
                original_filename=uploaded.name,
            )
        except PackageValidationError as exc:
            form.add_error("package", str(exc))
            return render(request, self.template_name, {"form": form})

        return redirect("bulletin-import-preview", pk=bulletin_import.pk)


class BulletinImportPreviewView(StaffRequiredMixin, View):
    template_name = "publications/bulletin_import_preview.html"

    def get(self, request, *args, **kwargs):
        bulletin_import = get_object_or_404(BulletinImport, pk=kwargs["pk"])
        image_urls = {img.image_id: img.file.url for img in bulletin_import.images.all()}
        context = {"bulletin_import": bulletin_import}
        context.update(build_bulletin_context(bulletin_import.data, image_urls))
        context["source_pdf_url"] = bulletin_import.source_pdf.url if bulletin_import.source_pdf else None
        return render(request, self.template_name, context)


class BulletinImportApplyView(StaffRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        bulletin_import = get_object_or_404(BulletinImport, pk=kwargs["pk"])
        if not bulletin_import.can_publish:
            messages.error(request, _("Cet import ne peut pas être publié (déjà traité ou en erreur)."))
            return redirect("bulletin-import-preview", pk=bulletin_import.pk)
        bulletin = apply_bulletin_import(bulletin_import, getattr(request.user, "profile", None))
        messages.success(request, _("Bulletin publié."))
        return redirect("bulletin-detail", pk=bulletin.pk)


class BulletinImportDiscardView(StaffRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        bulletin_import = get_object_or_404(BulletinImport, pk=kwargs["pk"])
        bulletin_import.delete()
        messages.success(request, _("Import abandonné."))
        return redirect("bulletin-import-upload")
