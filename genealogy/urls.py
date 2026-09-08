from django.urls import path

from .views import GedcomExportView, StoryCreateView, StoryDeleteView, StoryUpdateView

urlpatterns = [
    path("recits/nouveau/<int:person_pk>/", StoryCreateView.as_view(), name="story-create"),
    path("recits/<int:pk>/modifier/", StoryUpdateView.as_view(), name="story-update"),
    path("recits/<int:pk>/supprimer/", StoryDeleteView.as_view(), name="story-delete"),
    path("export/gedcom/", GedcomExportView.as_view(), name="gedcom-export"),
]
