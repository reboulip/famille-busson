import json
import mimetypes
import os

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Exists, F, OuterRef, ProtectedError, Q
from django.db.models.functions import Lower
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.cache import patch_vary_headers
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from annuaire.models import Person
from annuaire.views import StaffRequiredMixin

from .access import accessible_categories, accessible_documents, effective_groups, user_can_access_category
from .forms import CategoryForm, DocumentFileFormSet, DocumentForm
from .models import Category, Document, DocumentFile


def _redactor_initial_json(view):
    """Build the JSON payload used by the person-picker to pre-populate redactor."""
    request = view.request
    if request.method == "POST":
        pk = request.POST.get("redactor")
        person = Person.objects.filter(pk=pk).first() if pk and pk.isdigit() else None
    elif getattr(view, "object", None) is not None:
        person = view.object.redactor
    else:
        person = None
    return json.dumps([{"id": person.pk, "name": str(person)}] if person else [])


INLINE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"}

DOCUMENT_SORTS = {
    "recent": ("-created_at", "-pk"),
    "deposit_asc": ("created_at", "pk"),
    "title_asc": (Lower("title"), "pk"),
    "title_desc": (Lower("title").desc(), "-pk"),
    "redactor_asc": (Lower("redactor__last_name").asc(nulls_last=True), Lower("redactor__first_name"), "pk"),
    "redactor_desc": (Lower("redactor__last_name").desc(nulls_last=True), "-pk"),
    "date_asc": (F("document_date").asc(nulls_last=True), "-pk"),
    "date_desc": (F("document_date").desc(nulls_last=True), "-pk"),
}
DEFAULT_DOCUMENT_SORT = "recent"


class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = "documents/category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return Category.objects.all().prefetch_related("groups").order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["root_categories"] = [c for c in context["categories"] if c.parent_id is None]
        return context


class CategoryDetailView(LoginRequiredMixin, DetailView):
    model = Category
    template_name = "documents/category_detail.html"
    context_object_name = "category"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_access = user_can_access_category(self.request.user, self.object)
        context["can_access"] = can_access
        context["access_groups"] = effective_groups(self.object)
        ancestors = []
        node = self.object.parent
        while node is not None:
            ancestors.append(node)
            node = node.parent
        ancestors.reverse()
        context["ancestors"] = ancestors
        context["children"] = self.object.children.all()
        if can_access:
            context["documents"] = accessible_documents(self.request.user).filter(category=self.object)
        return context


class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = "documents/document_list.html"
    context_object_name = "documents"
    paginate_by = 20

    def _accessible_documents(self):
        # Walks every category in Python (documents/access.py) -- memoize per request
        # so get_queryset() and get_context_data()'s filter lists don't each pay for it.
        if not hasattr(self, "_accessible_documents_cache"):
            self._accessible_documents_cache = accessible_documents(self.request.user)
        return self._accessible_documents_cache

    def get_queryset(self):
        sort = self.request.GET.get("sort", DEFAULT_DOCUMENT_SORT)
        ordering = DOCUMENT_SORTS.get(sort, DOCUMENT_SORTS[DEFAULT_DOCUMENT_SORT])
        qs = self._accessible_documents().select_related("category", "redactor").order_by(*ordering)
        query = self.request.GET.get("q", "")
        if query:
            content_match = Exists(
                DocumentFile.objects.filter(document=OuterRef("pk"), extracted_text__icontains=query)
            )
            qs = qs.annotate(content_match=content_match).filter(
                Q(title__icontains=query) | Q(description__icontains=query) | Q(content_match=True)
            )
        category_id = self.request.GET.get("category", "")
        if category_id.isdigit():
            qs = qs.filter(category_id=category_id)
        redactor_id = self.request.GET.get("redactor", "")
        if redactor_id.isdigit():
            qs = qs.filter(redactor_id=redactor_id)
        year = self.request.GET.get("year", "")
        if year.isdigit():
            qs = qs.filter(document_date__year=year)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        context["selected_category"] = self.request.GET.get("category", "")
        context["selected_redactor"] = self.request.GET.get("redactor", "")
        context["selected_year"] = self.request.GET.get("year", "")
        sort = self.request.GET.get("sort", DEFAULT_DOCUMENT_SORT)
        context["sort"] = sort if sort in DOCUMENT_SORTS else DEFAULT_DOCUMENT_SORT
        context["filter_categories"] = accessible_categories(self.request.user).order_by("name")
        accessible = self._accessible_documents()
        context["filter_redactors"] = (
            Person.objects.filter(redacted_documents__in=accessible).distinct().order_by("last_name", "first_name")
        )
        context["filter_years"] = accessible.exclude(document_date__isnull=True).dates(
            "document_date", "year", order="DESC"
        )
        return context

    def get_template_names(self):
        """live_filter.js re-fetches this same URL and swaps in just the results,
        so an XHR gets the partial rather than the whole page (mirrors
        annuaire's DirectoryListView)."""
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return ["documents/_document_results.html"]
        return [self.template_name]

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        patch_vary_headers(response, ["X-Requested-With"])
        return response


class CategoryCreateView(StaffRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "documents/category_form.html"
    success_url = reverse_lazy("category-list")


class CategoryUpdateView(StaffRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "documents/category_form.html"
    success_url = reverse_lazy("category-list")


class CategoryDeleteView(StaffRequiredMixin, DeleteView):
    model = Category
    template_name = "documents/category_confirm_delete.html"
    success_url = reverse_lazy("category-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["document_count"] = self.object.documents.count()
        context["child_count"] = self.object.children.count()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request,
                "Impossible de supprimer cette catégorie : elle contient des documents ou des "
                "sous-catégories. Supprimez-les d'abord.",
            )
            return self.get(request, *args, **kwargs)


@method_decorator(xframe_options_sameorigin, name="dispatch")
class DocumentFileView(LoginRequiredMixin, View):
    """Serves a DocumentFile's `file` or `thumbnail` by pk only -- never by
    path, which kills path traversal outright. This is the ONLY way to reach
    a document's bytes: DocumentStorage.url() raises rather than producing a
    public URL. Access is re-checked on every request, independent of
    whatever list/detail view the client was browsing from."""

    variant = "file"

    def get(self, request, pk):
        document_file = get_object_or_404(DocumentFile, pk=pk)
        if not user_can_access_category(request.user, document_file.document.category):
            raise PermissionDenied("Vous n'avez pas accès à ce document.")

        field_file = document_file.thumbnail if self.variant == "thumbnail" else document_file.file
        if not field_file:
            raise Http404("Aucune vignette pour ce fichier.")

        filename = os.path.basename(field_file.name)
        safe_filename = filename.replace('"', "")
        extension = os.path.splitext(filename)[1].lower()
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        force_download = request.GET.get("download") == "1"
        inline = extension in INLINE_EXTENSIONS and not force_download
        disposition = "inline" if inline else "attachment"

        response = FileResponse(field_file.open("rb"), content_type=content_type)
        response["Content-Disposition"] = f'{disposition}; filename="{safe_filename}"'
        response["X-Content-Type-Options"] = "nosniff"
        return response


class UploaderOrStaffRequiredMixin(LoginRequiredMixin):
    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return obj
        profile = getattr(user, "profile", None)
        if profile is None or obj.uploaded_by_id != profile.pk:
            raise PermissionDenied("Vous n'êtes pas le déposant de ce document.")
        return obj


class DocumentDetailView(LoginRequiredMixin, DetailView):
    model = Document
    template_name = "documents/document_detail.html"
    context_object_name = "document"

    def get_queryset(self):
        return accessible_documents(self.request.user).prefetch_related("files")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = getattr(user, "profile", None)
        context["can_edit"] = (
            user.is_staff or user.is_superuser or (profile is not None and self.object.uploaded_by_id == profile.pk)
        )
        # preview_kind is a Python property, not a queryset-filterable field -- group
        # in Python over the already-prefetched files rather than issuing 3 queries.
        image_files, pdf_files, other_files = [], [], []
        for file in self.object.files.all():
            {"image": image_files, "pdf": pdf_files}.get(file.preview_kind, other_files).append(file)
        context["image_files"] = image_files
        context["pdf_files"] = pdf_files
        context["other_files"] = other_files
        return context


class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = "documents/document_form.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not hasattr(request.user, "profile"):
            messages.error(request, "Vous devez compléter votre profil avant de déposer un document.")
            return redirect("profile-create")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        category_id = self.request.GET.get("category", "")
        if category_id.isdigit():
            initial["category"] = int(category_id)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = DocumentFileFormSet(self.request.POST, self.request.FILES)
        else:
            context["formset"] = DocumentFileFormSet()
        context["redactor_initial_json"] = _redactor_initial_json(self)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if not formset.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            form.instance.uploaded_by = getattr(self.request.user, "profile", None)
            self.object = form.save()
            formset.instance = self.object
            formset.save()
        return redirect("document-detail", pk=self.object.pk)


class DocumentUpdateView(UploaderOrStaffRequiredMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    template_name = "documents/document_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = DocumentFileFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context["formset"] = DocumentFileFormSet(instance=self.object)
        context["redactor_initial_json"] = _redactor_initial_json(self)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if not formset.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
        return redirect("document-detail", pk=self.object.pk)


class DocumentDeleteView(UploaderOrStaffRequiredMixin, DeleteView):
    model = Document
    template_name = "documents/document_confirm_delete.html"
    success_url = reverse_lazy("document-list")
