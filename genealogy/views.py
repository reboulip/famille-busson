import json
from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DeleteView, UpdateView

from annuaire.models import Person
from annuaire.privacy import is_redacted
from photos.access import accessible_photos

from .forms import FormStory
from .gedcom.export import build_gedcom, collect_export_set
from .models import Story, StoryPhoto


def _save_story_photos(request, story: Story) -> None:
    """Reconciles StoryPhoto rows against the photo-picker's posted ids, in
    picker order. Never trusts an id the requesting user can't actually see --
    accessible_photos() re-scopes it, same discipline as the timeline render."""
    ids = [int(pk) for pk in request.POST.getlist("photos") if pk.isdigit()]
    allowed_ids = set(accessible_photos(request.user).filter(pk__in=ids).values_list("pk", flat=True))
    ordered_ids = [pk for pk in ids if pk in allowed_ids]

    StoryPhoto.objects.filter(story=story).exclude(photo_id__in=ordered_ids).delete()
    existing_ids = set(StoryPhoto.objects.filter(story=story).values_list("photo_id", flat=True))
    for order, photo_id in enumerate(ordered_ids):
        if photo_id in existing_ids:
            StoryPhoto.objects.filter(story=story, photo_id=photo_id).update(order=order)
        else:
            StoryPhoto.objects.create(story=story, photo_id=photo_id, order=order)


class StoryOwnerOrStaffRequiredMixin(LoginRequiredMixin):
    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return obj
        profile = getattr(user, "profile", None)
        if profile is None or obj.created_by_id != profile.pk:
            raise PermissionDenied("Vous n'êtes pas l'auteur de ce récit.")
        return obj


class StoryCreateView(LoginRequiredMixin, CreateView):
    """Any logged-in member may add a story for any person -- the same
    collaborative posture as tagging people in a photo or editing relations,
    not creator/staff-restricted (only editing/deleting is)."""

    model = Story
    form_class = FormStory
    template_name = "genealogy/story_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.person = get_object_or_404(Person, pk=kwargs["person_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["person"] = self.person
        context["photos_initial_json"] = "[]"
        return context

    def form_valid(self, form):
        form.instance.person = self.person
        form.instance.created_by = getattr(self.request.user, "profile", None)
        self.object = form.save()
        _save_story_photos(self.request, self.object)
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("personne-detail", kwargs={"pk": self.person.pk}) + "?tab=histoire"


class StoryUpdateView(StoryOwnerOrStaffRequiredMixin, UpdateView):
    model = Story
    form_class = FormStory
    template_name = "genealogy/story_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["person"] = self.object.person
        existing = StoryPhoto.objects.filter(story=self.object).select_related("photo").order_by("order")
        context["photos_initial_json"] = _photos_initial_json(existing)
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        _save_story_photos(self.request, self.object)
        return response

    def get_success_url(self):
        return reverse("personne-detail", kwargs={"pk": self.object.person_id}) + "?tab=histoire"


class StoryDeleteView(StoryOwnerOrStaffRequiredMixin, DeleteView):
    model = Story
    template_name = "genealogy/story_confirm_delete.html"

    def get_success_url(self):
        return reverse("personne-detail", kwargs={"pk": self.object.person_id}) + "?tab=histoire"


def _photos_initial_json(story_photos) -> str:
    return json.dumps([{"id": sp.photo_id, "name": sp.photo.caption or sp.photo.filename} for sp in story_photos])


class GedcomExportView(LoginRequiredMixin, View):
    """GEDCOM export of the person cards currently rendered in the
    centered-tree view -- same client-supplied `?ids=` pattern as the Excel
    export (FamilyTreeExportView), never a server-computed selection. Any
    logged-in member may export, same posture as the existing Excel export,
    which already hands every member's contact details to any logged-in
    member."""

    def get(self, request, *args, **kwargs):
        person_ids = []
        for raw_id in request.GET.getlist("ids"):
            try:
                person_ids.append(int(raw_id))
            except ValueError:
                continue

        persons, relations = collect_export_set(person_ids)
        payload = build_gedcom(persons, relations, redact=is_redacted)
        response = HttpResponse(payload, content_type="application/x-gedcom")
        response["Content-Disposition"] = f'attachment; filename="genealogie-{date.today():%Y-%m-%d}.ged"'
        return response
