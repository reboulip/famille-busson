import mimetypes
import os

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from annuaire.views import StaffRequiredMixin

from .access import accessible_categories, accessible_documents, user_can_access_category
from .forms import CategoryForm
from .models import Category, Document, DocumentFile

INLINE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"}


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
        if can_access:
            context["documents"] = accessible_documents(self.request.user).filter(category=self.object)
        return context


class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = "documents/document_list.html"
    context_object_name = "documents"
    paginate_by = 20

    def get_queryset(self):
        qs = accessible_documents(self.request.user).select_related("category").order_by("-created_at")
        query = self.request.GET.get("q", "")
        if query:
            qs = qs.filter(Q(title__icontains=query) | Q(description__icontains=query))
        category_id = self.request.GET.get("category", "")
        if category_id.isdigit():
            qs = qs.filter(category_id=category_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        context["selected_category"] = self.request.GET.get("category", "")
        context["filter_categories"] = accessible_categories(self.request.user).order_by("name")
        return context


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
