from django.urls import path

from .views import (
    AlbumCreateView,
    AlbumDeleteView,
    AlbumDetailView,
    AlbumListView,
    AlbumUpdateView,
    PhotoFileView,
    PhotoTagView,
    PhotoUploadView,
)

urlpatterns = [
    path("", AlbumListView.as_view(), name="album-list"),
    path("nouveau/", AlbumCreateView.as_view(), name="album-create"),
    path("<int:pk>/", AlbumDetailView.as_view(), name="album-detail"),
    path("<int:pk>/televerser/", PhotoUploadView.as_view(), name="photo-upload"),
    path("<int:pk>/modifier/", AlbumUpdateView.as_view(), name="album-edit"),
    path("<int:pk>/supprimer/", AlbumDeleteView.as_view(), name="album-delete"),
    path("photos/<int:pk>/", PhotoFileView.as_view(variant="file"), name="photo-file"),
    path("photos/<int:pk>/web/", PhotoFileView.as_view(variant="web"), name="photo-file-web"),
    path("photos/<int:pk>/vignette/", PhotoFileView.as_view(variant="thumbnail"), name="photo-file-thumbnail"),
    path("photos/<int:pk>/personnes/", PhotoTagView.as_view(), name="photo-tag"),
]
