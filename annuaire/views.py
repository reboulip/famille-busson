import json
import logging
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_not_required, login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView, PasswordResetConfirmView, PasswordResetDoneView, PasswordResetView
from django.core.exceptions import PermissionDenied
from django.core.mail import get_connection, send_mail
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, TemplateView, UpdateView, View
from django.views.static import serve as static_serve

from .family_tree import build_family_chart_data, find_components
from .forms import (
    AddPresenceForm,
    AddRelationForm,
    BulkAccountCreateForm,
    ChaletForm,
    ChaletUpdateForm,
    CustomAuthenticationForm,
    ForcedPasswordChangeForm,
    FormSettings,
    PresenceForm,
    ProfileEditForm,
    SignupForm,
    UpdateRelationForm,
)
from .models import Account, Chalet, Person, PresencePSV, Relation


@login_required
def media_serve(request, path):
    return static_serve(request, path, document_root=settings.MEDIA_ROOT)


@login_required
def home(request):
    import datetime

    from publications.models import BlogPost, Comment

    recent_persons = Person.objects.all().order_by("-pk")[:6]
    recent_posts = BlogPost.objects.prefetch_related("authors").order_by("-created_at")[:5]
    recent_comments = Comment.objects.select_related("post", "author").order_by("-created_at")[:5]
    chalets = Chalet.objects.all().order_by("name")[:6]
    today = datetime.date.today()
    upcoming_presences = (
        PresencePSV.objects.filter(end_date__gte=today).select_related("person", "chalet").order_by("start_date")[:5]
    )
    return render(
        request,
        "annuaire/home.html",
        {
            "recent_persons": recent_persons,
            "recent_posts": recent_posts,
            "recent_comments": recent_comments,
            "chalets": chalets,
            "upcoming_presences": upcoming_presences,
        },
    )


@login_required
def my_profile(request):
    try:
        person = Person.objects.get(account=request.user)
        return redirect("personne-detail", pk=person.pk)
    except Person.DoesNotExist:
        return redirect("profile-create")


@login_required
def edit_my_profile(request):
    try:
        person = Person.objects.get(account=request.user)
        return redirect("person-edit", pk=person.pk)
    except Person.DoesNotExist:
        return redirect("profile-create")


class StaffRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class CustomLoginView(LoginView):
    template_name = "annuaire/login.html"
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        if user.must_change_password:
            return redirect("password-change-forced")
        if hasattr(user, "profile"):
            return redirect(self.get_success_url())
        else:
            return redirect("profile-create")

    def get_default_redirect_url(self):
        return reverse_lazy("home")


@method_decorator(login_not_required, name="dispatch")
class SignupView(FormView):
    template_name = "annuaire/signup.html"
    form_class = SignupForm
    success_url = reverse_lazy("edit-my-profile")

    def form_valid(self, form):
        email = form.cleaned_data.get("email")
        password = form.cleaned_data.get("password")

        if not Person.objects.filter(email=email).exists():
            messages.error(self.request, "Adresse email non reconnue, vous ne pouvez pas créer de compte.")
            return self.form_invalid(form)
        elif Account.objects.filter(email=email).exists():
            messages.error(self.request, "Un compte avec cet email existe déjà.")
            return redirect("login")
        else:
            user = Account.objects.create_user(email=email)
            user.set_password(password)
            user.save()
            login(self.request, user)
            return super().form_valid(form)


def _build_password_reset_url(request, account):
    uid = urlsafe_base64_encode(force_bytes(account.pk))
    token = default_token_generator.make_token(account)
    return request.build_absolute_uri(reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token}))


def _send_account_setup_email(request, email, reset_url, is_reset, connection=None):
    """Best-effort: one recipient's SMTP failure must not lose the others'
    accounts (already created) or hide their reset link (still shown on screen
    regardless -- see bulk_account_create.html)."""
    subject = "Votre mot de passe a été réinitialisé" if is_reset else "Votre compte Famille Busson"
    intro = (
        "Le mot de passe de votre compte sur le site de la famille Busson a été réinitialisé."
        if is_reset
        else "Un compte a été créé pour vous sur le site de la famille Busson."
    )
    message = (
        f"Bonjour,\n\n"
        f"{intro}\n\n"
        f"Adresse : {email}\n\n"
        f"Choisissez votre mot de passe ici : {reset_url}\n"
        f"Ce lien est à usage unique et expire dans 7 jours.\n\n"
        f"À bientôt !"
    )
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False, connection=connection)
        return True
    except Exception:
        logging.getLogger("django").exception("Failed to send account setup email to %s", email)
        return False


class BulkAccountCreateView(StaffRequiredMixin, FormView):
    template_name = "annuaire/bulk_account_create.html"
    form_class = BulkAccountCreateForm

    # Sending each email over a fresh, unshared SMTP connection is what pushed a
    # ~30-account batch past the provider's per-request timeout. Reuse one
    # connection across the batch, cycling it periodically so a long-lived
    # connection doesn't itself get dropped/rate-limited by the provider.
    _EMAILS_PER_CONNECTION = 15

    def form_valid(self, form):
        emails = form.cleaned_data["emails"]
        results = []
        reset_emails = []
        failed_emails = []
        errored_emails = []

        connection = get_connection()
        connection.open()
        sent_since_reconnect = 0

        try:
            for email in emails:
                try:
                    existing = Account.objects.filter(email=email).first()
                    is_reset = bool(existing)
                    account = existing or Account(email=email)
                    account.set_password(secrets.token_urlsafe(32))
                    account.save()
                except Exception:
                    logging.getLogger("django").exception("Failed to create account for %s", email)
                    errored_emails.append(email)
                    results.append({"email": email, "status": "error", "email_sent": False, "reset_url": None})
                    continue

                if is_reset:
                    reset_emails.append(email)

                if sent_since_reconnect >= self._EMAILS_PER_CONNECTION:
                    connection.close()
                    connection = get_connection()
                    connection.open()
                    sent_since_reconnect = 0

                reset_url = _build_password_reset_url(self.request, account)
                email_sent = _send_account_setup_email(self.request, email, reset_url, is_reset, connection=connection)
                sent_since_reconnect += 1
                if not email_sent:
                    failed_emails.append(email)
                    # the connection may be in a broken state after a failed send;
                    # force a fresh one so one bad send doesn't take the rest of the
                    # batch down with it
                    connection.close()
                    connection = get_connection()
                    connection.open()
                    sent_since_reconnect = 0
                results.append(
                    {
                        "email": email,
                        "status": "reset" if is_reset else "created",
                        "email_sent": email_sent,
                        "reset_url": reset_url,
                    }
                )
        finally:
            connection.close()

        if reset_emails:
            messages.warning(
                self.request,
                "Mot de passe réinitialisé pour : " + ", ".join(reset_emails),
            )
        if failed_emails:
            messages.error(
                self.request,
                "Échec de l'envoi de l'email pour : "
                + ", ".join(failed_emails)
                + " — communiquez le mot de passe temporaire manuellement.",
            )
        if errored_emails:
            messages.error(
                self.request,
                "Échec de la création du compte pour : " + ", ".join(errored_emails),
            )

        return self.render_to_response(self.get_context_data(form=BulkAccountCreateForm(), results=results))


@login_required
def person_search_ajax(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})
    exclude_ids = [int(x) for x in request.GET.get("exclude", "").split(",") if x.isdigit()]
    # Note: icontains is case-insensitive but accent-sensitive on SQLite — "Bus" will not match "Büsson".
    # Revisit with the unaccent extension when moving to PostgreSQL.
    qs = (
        Person.objects.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q))
        .exclude(pk__in=exclude_ids)
        .order_by("last_name", "first_name")[:10]
    )
    return JsonResponse({"results": [{"id": p.pk, "name": str(p)} for p in qs]})


@login_required
def check_emails_ajax(request):
    if not request.user.is_staff:
        return JsonResponse({"error": "Forbidden"}, status=403)
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        emails = data.get("emails", [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    existing = list(Account.objects.filter(email__in=emails).values_list("email", flat=True))
    return JsonResponse({"existing": existing})


class ForcedPasswordChangeView(LoginRequiredMixin, FormView):
    template_name = "annuaire/password_change_forced.html"

    def get_form(self, form_class=None):
        if self.request.method == "POST":
            return ForcedPasswordChangeForm(self.request.user, self.request.POST)
        return ForcedPasswordChangeForm(self.request.user)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        user = self.request.user
        user.set_password(form.cleaned_data["new_password"])
        user.must_change_password = False
        user.save()
        update_session_auth_hash(self.request, user)
        messages.success(self.request, "Votre mot de passe a été mis à jour.")
        return redirect("my-profile")

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        from django.contrib.auth.password_validation import password_validators_help_texts

        context = super().get_context_data(**kwargs)
        if "form" not in context:
            context["form"] = self.get_form()
        context["password_hints"] = password_validators_help_texts()
        return context


class AccountPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "annuaire/password_reset_confirm.html"
    post_reset_login = True
    success_url = reverse_lazy("my-profile")

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.user.must_change_password:
            self.user.must_change_password = False
            self.user.save(update_fields=["must_change_password"])
        return response


class AccountPasswordResetView(PasswordResetView):
    template_name = "annuaire/password_reset.html"
    email_template_name = "annuaire/password_reset_email.txt"
    subject_template_name = "annuaire/password_reset_subject.txt"
    success_url = reverse_lazy("password-reset-done")


class AccountPasswordResetDoneView(PasswordResetDoneView):
    template_name = "annuaire/password_reset_done.html"


class ProfileCreateView(LoginRequiredMixin, CreateView):
    model = Person
    form_class = ProfileEditForm
    template_name = "annuaire/profile_create.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, "profile"):
            return redirect("my-profile")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "settings_form" not in context:
            context["settings_form"] = FormSettings()
        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        settings_form = FormSettings(request.POST)
        if form.is_valid() and settings_form.is_valid():
            return self.forms_valid(form, settings_form)
        return self.render_to_response(self.get_context_data(form=form, settings_form=settings_form))

    def forms_valid(self, form, settings_form):
        person = form.save(commit=False)
        person.account = self.request.user
        person.save()
        # Settings is auto-created by the Person post_save signal (see
        # annuaire/signals.py); layer the submitted opt-ins on top of it.
        person.settings.notify_on_birthday = settings_form.cleaned_data["notify_on_birthday"]
        person.settings.notify_on_new_blog_post = settings_form.cleaned_data["notify_on_new_blog_post"]
        person.settings.save()
        return redirect("personne-detail", pk=person.pk)


class DirectoryListView(LoginRequiredMixin, ListView):
    model = Person
    template_name = "annuaire/annuaire_list.html"
    context_object_name = "persons"

    def get_queryset(self):
        q = self.request.GET.get("q", "")
        qs = Person.objects.all().order_by("last_name", "first_name")
        if q:
            qs = qs.filter(Q(last_name__icontains=q) | Q(first_name__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        return context


class MapListView(LoginRequiredMixin, ListView):
    model = Person
    template_name = "annuaire/carte.html"
    context_object_name = "persons"

    def get_queryset(self):
        return (
            Person.objects.exclude(latitude__isnull=True)
            .exclude(longitude__isnull=True)
            .order_by("last_name", "first_name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["unresolved_count"] = Person.objects.filter(
            Q(latitude__isnull=True) | Q(longitude__isnull=True)
        ).count()
        context["persons_json"] = json.dumps(
            [
                {
                    "name": f"{person.first_name} {person.last_name}",
                    "lat": float(person.latitude),
                    "lon": float(person.longitude),
                    "url": reverse("personne-detail", kwargs={"pk": person.pk}),
                    "avatar": person.profile_photo.url
                    if person.profile_photo
                    else static("default_profile_picture.png"),
                }
                for person in context["persons"]
            ]
        )
        chalets = Chalet.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True).order_by("name")
        context["unresolved_chalet_count"] = Chalet.objects.filter(
            Q(latitude__isnull=True) | Q(longitude__isnull=True)
        ).count()
        context["chalets_json"] = json.dumps(
            [
                {
                    "name": chalet.name,
                    "lat": float(chalet.latitude),
                    "lon": float(chalet.longitude),
                    "url": reverse("chalet-detail", kwargs={"pk": chalet.pk}),
                    # No default chalet photo asset (unlike Person's default avatar) -- the
                    # "emoji::" sentinel tells map_init.js to render the 🏔️ placeholder used
                    # everywhere else in the app (chalet_list.html, chalet_detail.html)
                    # instead of trying to load an image that doesn't exist.
                    "avatar": chalet.photo.url if chalet.photo else "emoji::🏔️",
                }
                for chalet in chalets
            ]
        )
        return context


class FamilyTreeView(LoginRequiredMixin, TemplateView):
    template_name = "annuaire/genealogie.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = build_family_chart_data()
        components = find_components(data)
        context["graph_json"] = json.dumps(data)
        context["components_json"] = json.dumps(components)

        pk = kwargs.get("pk")
        if pk is not None:
            person = get_object_or_404(Person, pk=pk)
            context["main_id"] = str(person.pk)
        else:
            context["main_id"] = components[0]["root_id"] if components else None

        return context


class ProfileDetailView(LoginRequiredMixin, DetailView):
    model = Person
    template_name = "annuaire/personne_detail.html"
    context_object_name = "person"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = self.get_object()

        partner_relation = Relation.objects.filter(
            Q(person1=person) | Q(person2=person), relationship_type__in=[0, 1]
        ).first()
        if partner_relation:
            if partner_relation.person1 == person:
                partner = partner_relation.person2
            else:
                partner = partner_relation.person1
            context["partner"] = partner
            context["partner_type"] = partner_relation.get_relationship_type_display()

        parent_relations = Relation.objects.filter(person1=person, relationship_type=2)
        context["parents"] = [rel.person2 for rel in parent_relations]

        child_relations = Relation.objects.filter(person1=person, relationship_type=3)
        context["children"] = [rel.person2 for rel in child_relations]

        user = self.request.user
        profile = getattr(user, "profile", None)
        context["can_edit"] = user.is_staff or user.is_superuser or profile == person

        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Person
    form_class = ProfileEditForm
    template_name = "annuaire/update_form.html"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return obj
        if obj != getattr(user, "profile", None):
            raise PermissionDenied("Vous ne pouvez pas éditer ce profil car ce n'est pas le vôtre.")
        return obj

    def get_success_url(self):
        user = self.request.user
        if self.object == getattr(user, "profile", None):
            return reverse_lazy("my-profile")
        return reverse_lazy("personne-detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["formsets"] = []
        return data


def _get_person_for_relations_edit(request, pk):
    person = get_object_or_404(Person, pk=pk)
    user = request.user
    if user.is_staff or user.is_superuser:
        return person
    if person.account_id != user.pk:
        raise PermissionDenied("Vous ne pouvez modifier que vos propres relations.")
    return person


class PersonRelationsView(LoginRequiredMixin, View):
    template_name = "annuaire/person_relations_form.html"

    def get(self, request, *args, **kwargs):
        person = _get_person_for_relations_edit(request, kwargs["pk"])
        relations = (
            Relation.objects.filter(person1=person)
            .select_related("person2")
            .order_by("person2__last_name", "person2__first_name")
        )
        row_forms = [(rel, UpdateRelationForm(instance=rel, prefix=f"rel-{rel.pk}")) for rel in relations]
        return render(
            request,
            self.template_name,
            {
                "person": person,
                "row_forms": row_forms,
                "add_form": AddRelationForm(),
            },
        )


class AddRelationView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        person = _get_person_for_relations_edit(request, kwargs["pk"])
        form = AddRelationForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Formulaire invalide. Vérifiez la personne et le type de relation.")
            return redirect("person-relations-edit", pk=person.pk)
        relation = form.save(commit=False)
        if relation.person2 == person:
            messages.error(request, "Une personne ne peut pas être en relation avec elle-même.")
            return redirect("person-relations-edit", pk=person.pk)
        if Relation.objects.filter(person1=person, person2=relation.person2).exists():
            messages.error(request, "Une relation avec cette personne existe déjà.")
            return redirect("person-relations-edit", pk=person.pk)
        relation.person1 = person
        relation.save()
        return redirect("person-relations-edit", pk=person.pk)


class UpdateRelationView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        person = _get_person_for_relations_edit(request, kwargs["pk"])
        relation = get_object_or_404(Relation, pk=kwargs["rid"], person1=person)
        form = UpdateRelationForm(request.POST, instance=relation, prefix=f"rel-{relation.pk}")
        if form.is_valid():
            form.save()
        else:
            messages.error(request, "Modification invalide.")
        return redirect("person-relations-edit", pk=person.pk)


class DeleteRelationView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        person = _get_person_for_relations_edit(request, kwargs["pk"])
        relation = get_object_or_404(Relation, pk=kwargs["rid"], person1=person)
        relation.delete()
        return redirect("person-relations-edit", pk=person.pk)


class ChaletListView(LoginRequiredMixin, ListView):
    model = Chalet
    template_name = "annuaire/chalet_list.html"
    context_object_name = "chalets"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        presences = PresencePSV.objects.select_related("person", "chalet").order_by("start_date")
        context["presences_json"] = json.dumps(
            [
                {
                    "person": str(p.person),
                    "chalet": p.chalet.name,
                    "start": p.start_date.isoformat(),
                    "end": p.end_date.isoformat(),
                }
                for p in presences
            ]
        )
        return context


def _owners_initial_json(view):
    """Build the JSON payload used by the person-picker to pre-populate owners."""
    request = view.request
    if request.method == "POST":
        ids = [int(pk) for pk in request.POST.getlist("owners") if pk.isdigit()]
        persons = list(Person.objects.filter(pk__in=ids).order_by("last_name", "first_name"))
    else:
        profile = getattr(request.user, "profile", None)
        persons = [profile] if profile is not None else []
    return json.dumps([{"id": p.pk, "name": str(p)} for p in persons])


class ChaletCreateView(LoginRequiredMixin, CreateView):
    model = Chalet
    form_class = ChaletForm
    template_name = "annuaire/chalet_form.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not hasattr(request.user, "profile"):
            messages.error(request, "Vous devez compléter votre profil avant de créer un chalet.")
            return redirect("profile-create")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["current_person"] = getattr(self.request.user, "profile", None)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_owner_picker"] = True
        context["owners_initial_json"] = _owners_initial_json(self)
        return context

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            profile = getattr(self.request.user, "profile", None)
            if profile is not None and not self.object.owners.filter(pk=profile.pk).exists():
                self.object.owners.add(profile)
        return redirect("chalet-detail", pk=self.object.pk)


class ChaletOwnerOrStaffMixin(LoginRequiredMixin):
    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return obj
        profile = getattr(user, "profile", None)
        if profile is None or not obj.owners.filter(pk=profile.pk).exists():
            raise PermissionDenied("Vous n'êtes pas propriétaire de ce chalet.")
        return obj


class ChaletDetailView(LoginRequiredMixin, DetailView):
    model = Chalet
    template_name = "annuaire/chalet_detail.html"
    context_object_name = "chalet"

    def get_context_data(self, **kwargs):
        import datetime

        context = super().get_context_data(**kwargs)
        today = datetime.date.today()
        all_presences = PresencePSV.objects.filter(chalet=self.object).select_related("person").order_by("start_date")
        all_presences = list(all_presences)
        context["past_presences"] = [p for p in all_presences if p.end_date < today]
        context["current_presences"] = [p for p in all_presences if p.start_date <= today <= p.end_date]
        context["future_presences"] = [p for p in all_presences if p.start_date > today]
        context["presence_form"] = AddPresenceForm()
        context["presences_json"] = json.dumps(
            [
                {
                    "person": str(p.person),
                    "chalet": self.object.name,
                    "start": p.start_date.isoformat(),
                    "end": p.end_date.isoformat(),
                }
                for p in all_presences
            ]
        )
        user = self.request.user
        profile = getattr(user, "profile", None)
        context["can_edit_chalet"] = (
            user.is_staff
            or user.is_superuser
            or (profile is not None and self.object.owners.filter(pk=profile.pk).exists())
        )
        return context


class ChaletUpdateView(ChaletOwnerOrStaffMixin, UpdateView):
    model = Chalet
    form_class = ChaletUpdateForm
    template_name = "annuaire/chalet_form.html"

    def get_success_url(self):
        return reverse_lazy("chalet-detail", kwargs={"pk": self.object.pk})


class ChaletOwnersUpdateView(ChaletOwnerOrStaffMixin, DetailView):
    model = Chalet
    template_name = "annuaire/chalet_owners_form.html"
    context_object_name = "chalet"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        owners = self.object.owners.all().order_by("last_name", "first_name")
        context["owners"] = owners
        context["owners_initial_json"] = json.dumps([{"id": p.pk, "name": str(p)} for p in owners])
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        owner_ids = [int(pk) for pk in request.POST.getlist("owners") if pk.isdigit()]
        self.object.owners.set(Person.objects.filter(pk__in=owner_ids))
        return redirect("chalet-detail", pk=self.object.pk)


class AddPresenceView(LoginRequiredMixin, FormView):
    form_class = AddPresenceForm

    def get_success_url(self):
        return reverse_lazy("chalet-detail", kwargs={"pk": self.kwargs["pk"]})

    def form_valid(self, form):
        chalet_id = self.kwargs["pk"]
        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]
        for person in form.cleaned_data["persons"]:
            PresencePSV.objects.create(chalet_id=chalet_id, person=person, start_date=start_date, end_date=end_date)
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Erreur dans le formulaire de présence.")
        return redirect("chalet-detail", pk=self.kwargs["pk"])


class UpdatePresenceView(LoginRequiredMixin, UpdateView):
    model = PresencePSV
    form_class = PresenceForm
    template_name = "annuaire/presence_form.html"
    pk_url_kwarg = "presence_pk"

    def get_success_url(self):
        return reverse_lazy("chalet-detail", kwargs={"pk": self.kwargs["pk"]})


class DeletePresenceView(LoginRequiredMixin, DeleteView):
    model = PresencePSV
    pk_url_kwarg = "presence_pk"

    def get(self, request, *args, **kwargs):
        return redirect("chalet-detail", pk=self.kwargs["pk"])

    def get_success_url(self):
        return reverse_lazy("chalet-detail", kwargs={"pk": self.kwargs["pk"]})
