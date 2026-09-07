import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from annuaire.models import Person
from annuaire.views import can_edit_person

from .access import accessible_events, effective_groups
from .forms import EventForm, RsvpForm
from .models import Event, Rsvp


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

        # RSVP -- anyone the requester can answer for (themself, plus any
        # accountless profile they own), same rule as annuaire.can_edit_person.
        answerable_persons = []
        if profile is not None:
            answerable_persons.append(profile)
            answerable_persons.extend(profile.managed_profiles.all())
        existing_rsvps = {r.person_id: r for r in self.object.rsvps.select_related("person")}
        context["rsvp_rows"] = [(person, existing_rsvps.get(person.pk)) for person in answerable_persons]
        context["attendees"] = list(
            self.object.rsvps.filter(response="yes").select_related("person").order_by("person__last_name")
        )
        headcount = self.object.rsvps.filter(response="yes").aggregate(count=Count("id"), extra=Sum("guest_count"))
        context["attendee_headcount"] = (headcount["count"] or 0) + (headcount["extra"] or 0)
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


class EventRsvpView(LoginRequiredMixin, View):
    """POST-only participation endpoint, mirroring PhotoTagView's shape
    (access-checked, redirect back). Any member who can access the event may
    RSVP on behalf of anyone they can_edit_person() for -- the same rule that
    lets a parent answer for an accountless child."""

    def post(self, request, pk):
        event = get_object_or_404(accessible_events(request.user), pk=pk)
        person_id = request.POST.get("person", "")
        person = get_object_or_404(Person, pk=person_id) if person_id.isdigit() else None
        if person is None or not can_edit_person(request.user, person):
            raise PermissionDenied("Vous ne pouvez pas répondre pour cette personne.")

        form = RsvpForm(request.POST)
        if form.is_valid():
            Rsvp.objects.update_or_create(
                event=event,
                person=person,
                defaults={
                    "response": form.cleaned_data["response"],
                    "guest_count": form.cleaned_data["guest_count"],
                    "note": form.cleaned_data["note"],
                },
            )
        return redirect("event-detail", pk=event.pk)
