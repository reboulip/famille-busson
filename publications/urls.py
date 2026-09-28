from django.urls import path

from .views import (
    BlogPostCreateView,
    BlogPostDeleteView,
    BlogPostDetailView,
    BlogPostListView,
    BlogPostUpdateView,
    BulletinDetailView,
    BulletinImportApplyView,
    BulletinImportDiscardView,
    BulletinImportPreviewView,
    BulletinImportUploadView,
    BulletinListView,
    CommentDeleteView,
)

urlpatterns = [
    path("", BlogPostListView.as_view(), name="blogpost-list"),
    path("new/", BlogPostCreateView.as_view(), name="blogpost-create"),
    path("<int:pk>/", BlogPostDetailView.as_view(), name="blogpost-detail"),
    path("<int:pk>/edit/", BlogPostUpdateView.as_view(), name="blogpost-edit"),
    path("<int:pk>/delete/", BlogPostDeleteView.as_view(), name="blogpost-delete"),
    path("comments/<int:pk>/delete/", CommentDeleteView.as_view(), name="comment-delete"),
    path("bulletins/", BulletinListView.as_view(), name="bulletin-list"),
    path("bulletins/import/", BulletinImportUploadView.as_view(), name="bulletin-import-upload"),
    path("bulletins/import/<int:pk>/", BulletinImportPreviewView.as_view(), name="bulletin-import-preview"),
    path("bulletins/import/<int:pk>/publier/", BulletinImportApplyView.as_view(), name="bulletin-import-apply"),
    path("bulletins/import/<int:pk>/abandonner/", BulletinImportDiscardView.as_view(), name="bulletin-import-discard"),
    path("bulletins/<int:pk>/", BulletinDetailView.as_view(), name="bulletin-detail"),
]
