import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
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

from .forms import AttachmentFormSet, BlogPostForm, CommentForm
from .models import BlogPost, Comment, Tag


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
            raise PermissionDenied("Vous n'êtes pas auteur de cette publication.")
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
            messages.error(request, "Vous devez compléter votre profil avant de commenter.")
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
            messages.error(request, "Vous devez compléter votre profil avant de publier.")
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


class CommentDeleteView(StaffRequiredMixin, DeleteView):
    model = Comment
    template_name = "publications/comment_confirm_delete.html"

    def get_success_url(self):
        return reverse("blogpost-detail", kwargs={"pk": self.object.post.pk})
