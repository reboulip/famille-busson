from django.urls import path

from .views import EventCreateView, EventDeleteView, EventDetailView, EventListView, EventRsvpView, EventUpdateView

urlpatterns = [
    path("", EventListView.as_view(), name="event-list"),
    path("nouveau/", EventCreateView.as_view(), name="event-create"),
    path("<int:pk>/", EventDetailView.as_view(), name="event-detail"),
    path("<int:pk>/modifier/", EventUpdateView.as_view(), name="event-edit"),
    path("<int:pk>/supprimer/", EventDeleteView.as_view(), name="event-delete"),
    path("<int:pk>/participation/", EventRsvpView.as_view(), name="event-rsvp"),
]
