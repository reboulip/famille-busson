from django.urls import path

from .views import (
    GedcomExportView,
    GedcomImportApplyView,
    GedcomImportDiscardView,
    GedcomImportReviewView,
    GedcomImportUploadView,
    StoryCreateView,
    StoryDeleteView,
    StoryUpdateView,
)

urlpatterns = [
    path("recits/nouveau/<int:person_pk>/", StoryCreateView.as_view(), name="story-create"),
    path("recits/<int:pk>/modifier/", StoryUpdateView.as_view(), name="story-update"),
    path("recits/<int:pk>/supprimer/", StoryDeleteView.as_view(), name="story-delete"),
    path("export/gedcom/", GedcomExportView.as_view(), name="gedcom-export"),
    path("import/", GedcomImportUploadView.as_view(), name="gedcom-import-upload"),
    path("import/<int:pk>/revision/", GedcomImportReviewView.as_view(), name="gedcom-import-review"),
    path("import/<int:pk>/appliquer/", GedcomImportApplyView.as_view(), name="gedcom-import-apply"),
    path("import/<int:pk>/abandonner/", GedcomImportDiscardView.as_view(), name="gedcom-import-discard"),
]
