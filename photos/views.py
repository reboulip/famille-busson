import json
import mimetypes
import os

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .access import effective_groups, user_can_access_album
from .forms import AlbumForm, PhotoUploadForm
from .models import Album, PersonTag, Photo

INLINE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

# Photo file bytes are access-checked; they must never sit in a shared/public
# cache, so `private` is not negotiable here (see PhotoFileView below).
FILE_CACHE_CONTROL = "private, max-age=604800"


class AlbumListView(LoginRequiredMixin, ListView):
    """ "Visible but locked" album list -- every album is listed, a locked one
    renders name-only with a lock badge (see the template), never
    Album.objects.all() *filtered*, which would hide it entirely."""

    model = Album
    template_name = "photos/album_list.html"
    context_object_name = "albums"

    def get_queryset(self):
        return (
            Album.objects.all()
            .select_related("cover")
            .prefetch_related("groups")
            .annotate(photo_count=Count("photos"))
        )


class AlbumDetailView(LoginRequiredMixin, ListView):
    """Paginated as a ListView over the album's own photos (with the album
    added to context), rather than DetailView + a hand-rolled Paginator --
    simpler, and GET-param pagination comes for free.

    Locked-album policy mirrors documents.CategoryDetailView: the album
    itself resolves via a plain get_object_or_404 (the page isn't secret),
    but its description/photos render only when user_can_access_album() is
    true -- otherwise a locked placeholder naming the unlocking group(s),
    with no leakage."""

    template_name = "photos/album_detail.html"
    context_object_name = "photos"
    paginate_by = 24

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.album = get_object_or_404(Album.objects.select_related("cover"), pk=kwargs["pk"])

    def get_queryset(self):
        if not user_can_access_album(self.request.user, self.album):
            return Photo.objects.none()
        return self.album.photos.chronological()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = getattr(user, "profile", None)
        context["album"] = self.album
        context["can_access"] = user_can_access_album(user, self.album)
        context["access_groups"] = effective_groups(self.album)
        context["can_edit"] = (
            user.is_staff or user.is_superuser or (profile is not None and self.album.created_by_id == profile.pk)
        )
        return context


class PhotoUploadView(LoginRequiredMixin, View):
    """Per-file XHR upload endpoint backing photo_upload.js's progress UI --
    one file per POST, unlike documents' hidden-formset transport, so
    xhr.upload.onprogress can report real per-file progress and one corrupt
    file never loses the rest of the batch. Any member who can access the
    album may upload into it (the same posture as tagging people in a
    photo -- collaborative, not uploader/staff-restricted)."""

    def post(self, request, pk):
        album = get_object_or_404(Album, pk=pk)
        if not user_can_access_album(request.user, album):
            raise PermissionDenied("Vous n'avez pas accès à cet album.")

        form = PhotoUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            error = next(iter(form.errors.get("file", [])), "Fichier invalide.")
            return JsonResponse({"error": error}, status=400)

        photo = form.save(commit=False)
        photo.album = album
        photo.uploaded_by = getattr(request.user, "profile", None)
        photo.save()

        return JsonResponse(
            {
                "id": photo.pk,
                "filename": photo.filename,
                "thumbnail_url": reverse("photo-file-thumbnail", kwargs={"pk": photo.pk}),
            }
        )


class PhotoTagView(LoginRequiredMixin, View):
    """Dedicated tagging page, reusing the generic person-picker component
    (never a bespoke one) -- there is no photo-detail page yet, a later item
    adds one and will link here instead of standing up its own destination.
    Any member who can access the photo's album may tag/untag people, the
    same collaborative posture as PhotoUploadView."""

    template_name = "photos/photo_tag_form.html"

    def _get_photo(self, pk):
        photo = get_object_or_404(Photo.objects.select_related("album"), pk=pk)
        if not user_can_access_album(self.request.user, photo.album):
            raise PermissionDenied("Vous n'avez pas accès à cette photo.")
        return photo

    def get(self, request, pk):
        photo = self._get_photo(pk)
        return render(request, self.template_name, self._context(photo))

    def post(self, request, pk):
        photo = self._get_photo(pk)
        person_ids = {int(raw) for raw in request.POST.getlist("persons") if raw.isdigit()}
        existing_ids = set(photo.person_tags.values_list("person_id", flat=True))

        photo.person_tags.filter(person_id__in=existing_ids - person_ids).delete()

        tagged_by = getattr(request.user, "profile", None)
        for person_id in person_ids - existing_ids:
            PersonTag.objects.create(photo=photo, person_id=person_id, tagged_by=tagged_by)

        return redirect("album-detail", pk=photo.album_id)

    def _context(self, photo):
        tagged = [tag.person for tag in photo.person_tags.select_related("person")]
        return {
            "photo": photo,
            "tagged_persons_initial_json": json.dumps([{"id": p.pk, "name": str(p)} for p in tagged]),
        }


class AlbumCreateView(LoginRequiredMixin, CreateView):
    model = Album
    form_class = AlbumForm
    template_name = "photos/album_form.html"

    def get_success_url(self):
        return reverse("album-detail", kwargs={"pk": self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not hasattr(request.user, "profile"):
            messages.error(request, "Vous devez compléter votre profil avant de créer un album.")
            return redirect("profile-create")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = getattr(self.request.user, "profile", None)
        return super().form_valid(form)


class AlbumOwnerOrStaffRequiredMixin(LoginRequiredMixin):
    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return obj
        profile = getattr(user, "profile", None)
        if profile is None or obj.created_by_id != profile.pk:
            raise PermissionDenied("Vous n'êtes pas le créateur de cet album.")
        return obj


class AlbumUpdateView(AlbumOwnerOrStaffRequiredMixin, UpdateView):
    model = Album
    form_class = AlbumForm
    template_name = "photos/album_form.html"

    def get_success_url(self):
        return reverse("album-detail", kwargs={"pk": self.object.pk})


class AlbumDeleteView(AlbumOwnerOrStaffRequiredMixin, DeleteView):
    model = Album
    template_name = "photos/album_confirm_delete.html"
    success_url = reverse_lazy("album-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["photo_count"] = self.object.photos.count()
        return context


@method_decorator(xframe_options_sameorigin, name="dispatch")
class PhotoFileView(LoginRequiredMixin, View):
    """Serves a Photo's `file`/`web`/`thumbnail` by pk only -- never by path,
    which kills path traversal outright. This is the ONLY way to reach a
    photo's bytes: PhotoStorage.url() raises rather than producing a public
    URL. Access is re-checked on every request, independent of whatever list
    the client was browsing from.

    Unlike documents.DocumentFileView's thumbnail variant (which 404s when
    absent), a missing derivative here falls back to the original -- 10.3
    generates derivatives asynchronously, so a 404 would mean visibly broken
    images in the window between upload and the queue picking up the job."""

    variant = "file"

    def get(self, request, pk):
        photo = get_object_or_404(Photo, pk=pk)
        if not user_can_access_album(request.user, photo.album):
            raise PermissionDenied("Vous n'avez pas accès à cette photo.")

        field_file = {"web": photo.web, "thumbnail": photo.thumbnail}.get(self.variant)
        if not field_file:
            field_file = photo.file
        if not field_file:
            raise Http404("Fichier introuvable.")

        filename = os.path.basename(field_file.name)
        safe_filename = filename.replace('"', "")
        extension = os.path.splitext(filename)[1].lower()
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        force_download = request.GET.get("download") == "1"
        inline = extension in INLINE_EXTENSIONS and not force_download
        disposition = "inline" if inline else "attachment"

        response = FileResponse(field_file.open("rb"), content_type=content_type)
        response["Content-Disposition"] = f'{disposition}; filename="{safe_filename}"'
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = FILE_CACHE_CONTROL
        return response
