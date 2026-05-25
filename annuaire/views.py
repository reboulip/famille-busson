import json
import secrets
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth import login, update_session_auth_hash
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.views.generic import DetailView, UpdateView, FormView, ListView, CreateView, DeleteView, View
from django.urls import reverse_lazy
from .models import Person, Account, Relation, Chalet, PresencePSV
from .forms import (
    ProfileEditForm, RelationEditFormSet, CustomAuthenticationForm,
    SignupForm, AddPresenceForm, PresenceForm, ChaletForm, ChaletUpdateForm,
    AddRelationForm, UpdateRelationForm,
    BulkAccountCreateForm, ForcedPasswordChangeForm,
)


def home(request):
    from publications.models import BlogPost, Comment
    recent_persons = Person.objects.all().order_by('-pk')[:6]
    recent_posts = (
        BlogPost.objects.prefetch_related('authors').order_by('-created_at')[:5]
    )
    recent_comments = (
        Comment.objects.select_related('post', 'author').order_by('-created_at')[:5]
    )
    return render(request, 'annuaire/home.html', {
        'recent_persons': recent_persons,
        'recent_posts': recent_posts,
        'recent_comments': recent_comments,
    })


@login_required
def my_profile(request):
    try:
        person = Person.objects.get(account=request.user)
        return redirect('personne-detail', pk=person.pk)
    except Person.DoesNotExist:
        return redirect('profile-create')


@login_required
def edit_my_profile(request):
    try:
        person = Person.objects.get(account=request.user)
        return redirect('person-edit', pk=person.pk)
    except Person.DoesNotExist:
        return redirect('profile-create')


class StaffRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class CustomLoginView(LoginView):
    template_name = 'annuaire/login.html'
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        if user.must_change_password:
            return redirect('password-change-forced')
        if hasattr(user, 'profile'):
            return redirect(self.get_success_url())
        else:
            return redirect('profile-create')

    def get_success_url(self):
        return reverse_lazy('home')


class SignupView(FormView):
    template_name = 'annuaire/signup.html'
    form_class = SignupForm
    success_url = reverse_lazy('edit-my-profile')

    def form_valid(self, form):
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')

        if not Person.objects.filter(email=email).exists():
            messages.error(self.request, "Adresse email non reconnue, vous ne pouvez pas créer de compte.")
            return self.form_invalid(form)
        elif Account.objects.filter(email=email).exists():
            messages.error(self.request, "Un compte avec cet email existe déjà.")
            return redirect('login')
        else:
            user = Account.objects.create_user(email=email)
            user.set_password(password)
            user.save()
            login(self.request, user)
            return super().form_valid(form)


class BulkAccountCreateView(StaffRequiredMixin, FormView):
    template_name = 'annuaire/bulk_account_create.html'
    form_class = BulkAccountCreateForm

    def form_valid(self, form):
        emails = form.cleaned_data['emails']
        results = []
        reset_emails = []

        for email in emails:
            temp_password = secrets.token_urlsafe(12)
            existing = Account.objects.filter(email=email).first()
            if existing:
                existing.set_password(temp_password)
                existing.must_change_password = True
                existing.save()
                results.append({'email': email, 'status': 'reset', 'temp_password': temp_password})
                reset_emails.append(email)
            else:
                account = Account(email=email, must_change_password=True)
                account.set_password(temp_password)
                account.save()
                results.append({'email': email, 'status': 'created', 'temp_password': temp_password})

        if reset_emails:
            messages.warning(
                self.request,
                "Mot de passe réinitialisé pour : " + ", ".join(reset_emails),
            )

        return self.render_to_response(self.get_context_data(form=BulkAccountCreateForm(), results=results))


@login_required
def person_search_ajax(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})
    exclude_ids = [int(x) for x in request.GET.get('exclude', '').split(',') if x.isdigit()]
    # Note: icontains is case-insensitive but accent-sensitive on SQLite — "Bus" will not match "Büsson".
    # Revisit with the unaccent extension when moving to PostgreSQL.
    qs = (Person.objects
          .filter(Q(first_name__icontains=q) | Q(last_name__icontains=q))
          .exclude(pk__in=exclude_ids)
          .order_by('last_name', 'first_name')[:10])
    return JsonResponse({'results': [{'id': p.pk, 'name': str(p)} for p in qs]})


@login_required
def check_emails_ajax(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
        emails = data.get('emails', [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    existing = list(Account.objects.filter(email__in=emails).values_list('email', flat=True))
    return JsonResponse({'existing': existing})


class ForcedPasswordChangeView(LoginRequiredMixin, FormView):
    template_name = 'annuaire/password_change_forced.html'

    def get_form(self, form_class=None):
        if self.request.method == 'POST':
            return ForcedPasswordChangeForm(self.request.user, self.request.POST)
        return ForcedPasswordChangeForm(self.request.user)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        user = self.request.user
        user.set_password(form.cleaned_data['new_password'])
        user.must_change_password = False
        user.save()
        update_session_auth_hash(self.request, user)
        messages.success(self.request, "Votre mot de passe a été mis à jour.")
        return redirect('my-profile')

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        from django.contrib.auth.password_validation import password_validators_help_texts
        context = super().get_context_data(**kwargs)
        if 'form' not in context:
            context['form'] = self.get_form()
        context['password_hints'] = password_validators_help_texts()
        return context


class ProfileCreateView(LoginRequiredMixin, CreateView):
    model = Person
    form_class = ProfileEditForm
    template_name = 'annuaire/profile_create.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            return redirect('my-profile')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        person = form.save(commit=False)
        person.account = self.request.user
        person.save()
        return redirect('personne-detail', pk=person.pk)


class DirectoryListView(LoginRequiredMixin, ListView):
    model = Person
    template_name = 'annuaire/annuaire_list.html'
    context_object_name = 'persons'

    def get_queryset(self):
        q = self.request.GET.get('q', '')
        qs = Person.objects.all().order_by('last_name', 'first_name')
        if q:
            qs = qs.filter(Q(last_name__icontains=q) | Q(first_name__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


class ProfileDetailView(LoginRequiredMixin, DetailView):
    model = Person
    template_name = 'annuaire/personne_detail.html'
    context_object_name = 'person'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = self.get_object()

        partner_relation = Relation.objects.filter(
            Q(person1=person) | Q(person2=person),
            relationship_type__in=[0, 1]
        ).first()
        if partner_relation:
            if partner_relation.person1 == person:
                partner = partner_relation.person2
            else:
                partner = partner_relation.person1
            context['partner'] = partner
            context['partner_type'] = partner_relation.get_relationship_type_display()

        parent_relations = Relation.objects.filter(person1=person, relationship_type=2)
        context['parents'] = [rel.person2 for rel in parent_relations]

        child_relations = Relation.objects.filter(person1=person, relationship_type=3)
        context['children'] = [rel.person2 for rel in child_relations]

        user = self.request.user
        profile = getattr(user, 'profile', None)
        context['can_edit'] = user.is_staff or user.is_superuser or profile == person

        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Person
    form_class = ProfileEditForm
    template_name = 'annuaire/update_form.html'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return obj
        if obj != getattr(user, 'profile', None):
            raise PermissionDenied("Vous ne pouvez pas éditer ce profil car ce n'est pas le vôtre.")
        return obj

    def get_success_url(self):
        user = self.request.user
        if self.object == getattr(user, 'profile', None):
            return reverse_lazy('my-profile')
        return reverse_lazy('personne-detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['formsets'] = []
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
    template_name = 'annuaire/person_relations_form.html'

    def get(self, request, *args, **kwargs):
        person = _get_person_for_relations_edit(request, kwargs['pk'])
        relations = (
            Relation.objects.filter(person1=person)
            .select_related('person2')
            .order_by('person2__last_name', 'person2__first_name')
        )
        row_forms = [
            (rel, UpdateRelationForm(instance=rel, prefix=f'rel-{rel.pk}'))
            for rel in relations
        ]
        return render(request, self.template_name, {
            'person': person,
            'row_forms': row_forms,
            'add_form': AddRelationForm(),
        })


class AddRelationView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        person = _get_person_for_relations_edit(request, kwargs['pk'])
        form = AddRelationForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Formulaire invalide. Vérifiez la personne et le type de relation.")
            return redirect('person-relations-edit', pk=person.pk)
        relation = form.save(commit=False)
        if relation.person2 == person:
            messages.error(request, "Une personne ne peut pas être en relation avec elle-même.")
            return redirect('person-relations-edit', pk=person.pk)
        if Relation.objects.filter(person1=person, person2=relation.person2).exists():
            messages.error(request, "Une relation avec cette personne existe déjà.")
            return redirect('person-relations-edit', pk=person.pk)
        relation.person1 = person
        relation.save()
        return redirect('person-relations-edit', pk=person.pk)


class UpdateRelationView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        person = _get_person_for_relations_edit(request, kwargs['pk'])
        relation = get_object_or_404(Relation, pk=kwargs['rid'], person1=person)
        form = UpdateRelationForm(request.POST, instance=relation, prefix=f'rel-{relation.pk}')
        if form.is_valid():
            form.save()
        else:
            messages.error(request, "Modification invalide.")
        return redirect('person-relations-edit', pk=person.pk)


class DeleteRelationView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        person = _get_person_for_relations_edit(request, kwargs['pk'])
        relation = get_object_or_404(Relation, pk=kwargs['rid'], person1=person)
        relation.delete()
        return redirect('person-relations-edit', pk=person.pk)


class ChaletListView(LoginRequiredMixin, ListView):
    model = Chalet
    template_name = 'annuaire/chalet_list.html'
    context_object_name = 'chalets'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        presences = (
            PresencePSV.objects.select_related('person', 'chalet')
            .order_by('start_date')
        )
        context['presences_json'] = json.dumps([
            {
                'person': str(p.person),
                'chalet': p.chalet.name,
                'start': p.start_date.isoformat(),
                'end': p.end_date.isoformat(),
            }
            for p in presences
        ])
        return context


class ChaletCreateView(StaffRequiredMixin, CreateView):
    model = Chalet
    form_class = ChaletForm
    template_name = 'annuaire/chalet_form.html'

    def get_success_url(self):
        return reverse_lazy('chalet-detail', kwargs={'pk': self.object.pk})


class ChaletOwnerOrStaffMixin(LoginRequiredMixin):
    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return obj
        profile = getattr(user, 'profile', None)
        if profile is None or not obj.owners.filter(pk=profile.pk).exists():
            raise PermissionDenied("Vous n'êtes pas propriétaire de ce chalet.")
        return obj


class ChaletDetailView(LoginRequiredMixin, DetailView):
    model = Chalet
    template_name = 'annuaire/chalet_detail.html'
    context_object_name = 'chalet'

    def get_context_data(self, **kwargs):
        import datetime
        context = super().get_context_data(**kwargs)
        today = datetime.date.today()
        all_presences = (
            PresencePSV.objects.filter(chalet=self.object)
            .select_related('person')
            .order_by('start_date')
        )
        all_presences = list(all_presences)
        context['past_presences'] = [p for p in all_presences if p.end_date < today]
        context['current_presences'] = [p for p in all_presences if p.start_date <= today <= p.end_date]
        context['future_presences'] = [p for p in all_presences if p.start_date > today]
        context['presence_form'] = AddPresenceForm()
        context['presences_json'] = json.dumps([
            {
                'person': str(p.person),
                'chalet': self.object.name,
                'start': p.start_date.isoformat(),
                'end': p.end_date.isoformat(),
            }
            for p in all_presences
        ])
        user = self.request.user
        profile = getattr(user, 'profile', None)
        context['can_edit_chalet'] = (
            user.is_staff or user.is_superuser
            or (profile is not None and self.object.owners.filter(pk=profile.pk).exists())
        )
        return context


class ChaletUpdateView(ChaletOwnerOrStaffMixin, UpdateView):
    model = Chalet
    form_class = ChaletUpdateForm
    template_name = 'annuaire/chalet_form.html'

    def get_success_url(self):
        return reverse_lazy('chalet-detail', kwargs={'pk': self.object.pk})


class ChaletOwnersUpdateView(ChaletOwnerOrStaffMixin, DetailView):
    model = Chalet
    template_name = 'annuaire/chalet_owners_form.html'
    context_object_name = 'chalet'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        owners = self.object.owners.all().order_by('last_name', 'first_name')
        context['owners'] = owners
        context['owners_initial_json'] = json.dumps(
            [{'id': p.pk, 'name': str(p)} for p in owners]
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        owner_ids = [int(pk) for pk in request.POST.getlist('owners') if pk.isdigit()]
        self.object.owners.set(Person.objects.filter(pk__in=owner_ids))
        return redirect('chalet-detail', pk=self.object.pk)


class AddPresenceView(LoginRequiredMixin, FormView):
    form_class = AddPresenceForm

    def get_success_url(self):
        return reverse_lazy('chalet-detail', kwargs={'pk': self.kwargs['pk']})

    def form_valid(self, form):
        chalet_id = self.kwargs['pk']
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        for person in form.cleaned_data['persons']:
            PresencePSV.objects.create(chalet_id=chalet_id, person=person, start_date=start_date, end_date=end_date)
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Erreur dans le formulaire de présence.")
        return redirect('chalet-detail', pk=self.kwargs['pk'])


class UpdatePresenceView(LoginRequiredMixin, UpdateView):
    model = PresencePSV
    form_class = PresenceForm
    template_name = 'annuaire/presence_form.html'
    pk_url_kwarg = 'presence_pk'

    def get_success_url(self):
        return reverse_lazy('chalet-detail', kwargs={'pk': self.kwargs['pk']})


class DeletePresenceView(LoginRequiredMixin, DeleteView):
    model = PresencePSV
    pk_url_kwarg = 'presence_pk'

    def get(self, request, *args, **kwargs):
        return redirect('chalet-detail', pk=self.kwargs['pk'])

    def get_success_url(self):
        return reverse_lazy('chalet-detail', kwargs={'pk': self.kwargs['pk']})
