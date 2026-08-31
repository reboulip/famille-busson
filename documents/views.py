from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError, Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from annuaire.views import StaffRequiredMixin

from .access import accessible_categories, accessible_documents, user_can_access_category
from .forms import CategoryForm
from .models import Category, Document


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
