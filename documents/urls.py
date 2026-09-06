from django.urls import path

from .views import (
    CategoryCreateView,
    CategoryDeleteView,
    CategoryDetailView,
    CategoryListView,
    CategoryUpdateView,
    DocumentCreateView,
    DocumentDeleteView,
    DocumentDetailView,
    DocumentFileView,
    DocumentListView,
    DocumentUpdateView,
    document_search_ajax,
)

urlpatterns = [
    path("", DocumentListView.as_view(), name="document-list"),
    path("new/", DocumentCreateView.as_view(), name="document-create"),
    path("search/", document_search_ajax, name="document-search-ajax"),
    path("<int:pk>/", DocumentDetailView.as_view(), name="document-detail"),
    path("<int:pk>/edit/", DocumentUpdateView.as_view(), name="document-edit"),
    path("<int:pk>/delete/", DocumentDeleteView.as_view(), name="document-delete"),
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("categories/new/", CategoryCreateView.as_view(), name="category-create"),
    path("categories/<int:pk>/", CategoryDetailView.as_view(), name="category-detail"),
    path("categories/<int:pk>/edit/", CategoryUpdateView.as_view(), name="category-edit"),
    path("categories/<int:pk>/delete/", CategoryDeleteView.as_view(), name="category-delete"),
    path("fichiers/<int:pk>/", DocumentFileView.as_view(variant="file"), name="document-file"),
    path(
        "fichiers/<int:pk>/vignette/",
        DocumentFileView.as_view(variant="thumbnail"),
        name="document-file-thumbnail",
    ),
]
