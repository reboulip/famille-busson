import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from annuaire.models import Person

from .access import accessible_events, effective_groups
from .forms import EventForm
from .models import Event


def _organisers_initial_json(view):
    """Build the JSON payload used by the person-picker to pre-populate
    organisers -- mirrors annuaire.views._owners_initial_json."""
    request = view.request
    if request.method == "POST":
        ids = [int(pk) for pk in request.POST.getlist("organisers") if pk.isdigit()]
        persons = list(Person.objects.filter(pk__in=ids).order_by("last_name", "first_name"))
    else:
        profile = getattr(request.user, "profile", None)
        persons = [profile] if profile is not None else []
    return json.dumps([{"id": p.pk, "name": str(p)} for p in persons])


class EventListView(LoginRequiredMixin, ListView):
    """Upcoming-only by default, with a "passés" toggle (?passes=1) -- mirrors
    ChaletDetailView's past/current/future split rather than a paginated
    all-events list. Locked events are invisible, never visible-but-locked."""

    model = Event
    template_name = "events/event_list.html"
    context_object_name = "events"

    def get_queryset(self):
        qs = accessible_events(self.request.user).prefetch_related("organisers")
        now = timezone.now()
        if self.request.GET.get("passes") == "1":
            return qs.past(now).order_by("-start", "-pk")
        return qs.upcoming(now)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["showing_past"] = self.request.GET.get("passes") == "1"
        return context


class EventDetailView(LoginRequiredMixin, DetailView):
    """Locked-event policy: the queryset itself is scoped to accessible_events(user),
    so a restricted event 404s directly -- never "visible but locked" like an
    Album/Category. See events/access.py."""

    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"

    def get_queryset(self):
        return accessible_events(self.request.user).prefetch_related("organisers", "groups")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = getattr(user, "profile", None)
        context["can_edit"] = (
            user.is_staff
            or user.is_superuser
            or (profile is not None and self.object.organisers.filter(pk=profile.pk).exists())
        )
        context["access_groups"] = effective_groups(self.object)
        return context


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not hasattr(request.user, "profile"):
            messages.error(request, "Vous devez compléter votre profil avant de créer un événement.")
            return redirect("profile-create")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["current_person"] = getattr(self.request.user, "profile", None)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organisers_initial_json"] = _organisers_initial_json(self)
        return context

    def form_valid(self, form):
        with transaction.atomic():
            form.instance.created_by = getattr(self.request.user, "profile", None)
            self.object = form.save()
            profile = getattr(self.request.user, "profile", None)
            # An event can never end up with zero organisers, even if the
            # picker's hidden inputs were tampered with or omitted -- mirrors
            # ChaletCreateView.form_valid()'s owners guarantee.
            if profile is not None and not self.object.organisers.filter(pk=profile.pk).exists():
                self.object.organisers.add(profile)
        return redirect("event-detail", pk=self.object.pk)


class EventOrganiserOrStaffMixin(LoginRequiredMixin):
    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return obj
        profile = getattr(user, "profile", None)
        if profile is None or not obj.organisers.filter(pk=profile.pk).exists():
            raise PermissionDenied("Vous n'êtes pas organisateur·rice de cet événement.")
        return obj


class EventUpdateView(EventOrganiserOrStaffMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organisers_initial_json"] = _organisers_initial_json(self)
        return context

    def get_success_url(self):
        return reverse("event-detail", kwargs={"pk": self.object.pk})


class EventDeleteView(EventOrganiserOrStaffMixin, DeleteView):
    model = Event
    template_name = "events/event_confirm_delete.html"

    def get_success_url(self):
        return reverse("event-list")
