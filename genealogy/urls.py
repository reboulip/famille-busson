from django.urls import path

from .views import StoryCreateView, StoryDeleteView, StoryUpdateView

urlpatterns = [
    path("nouveau/<int:person_pk>/", StoryCreateView.as_view(), name="story-create"),
    path("<int:pk>/modifier/", StoryUpdateView.as_view(), name="story-update"),
    path("<int:pk>/supprimer/", StoryDeleteView.as_view(), name="story-delete"),
]
