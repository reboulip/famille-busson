import json
import secrets
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth import login, update_session_auth_hash
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.views.generic import DetailView, UpdateView, FormView, ListView, CreateView, DeleteView
from django.urls import reverse_lazy
from .models import Person, Account, Relation, Chalet, PresencePSV
from .forms import (
    ProfileEditForm, RelationEditFormSet, CustomAuthenticationForm,
    SignupForm, PresenceForm, ChaletForm, BulkAccountCreateForm, ForcedPasswordChangeForm,
)


def home(request):
    recent_persons = Person.objects.all().order_by('-pk')[:6]
    return render(request, 'annuaire/home.html', {'recent_persons': recent_persons})


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

        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Person
    form_class = ProfileEditForm
    template_name = 'annuaire/update_form.html'
    success_url = reverse_lazy('my-profile')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        if obj != self.request.user.profile:
            raise PermissionDenied("Vous ne pouvez pas éditer ce profil car ce n'est pas le vôtre.")
        return obj

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['formsets'] = [RelationEditFormSet(self.request.POST, instance=self.object)]
        else:
            data['formsets'] = [RelationEditFormSet(instance=self.object)]
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        form_relations = context['formsets'][0]
        self.object = form.save()
        if form_relations.is_valid():
            form_relations.instance = self.object
            form_relations.save()
        else:
            return super().form_invalid(form)
        return super().form_valid(form)


class ChaletListView(LoginRequiredMixin, ListView):
    model = Chalet
    template_name = 'annuaire/chalet_list.html'
    context_object_name = 'chalets'


class ChaletCreateView(StaffRequiredMixin, CreateView):
    model = Chalet
    form_class = ChaletForm
    template_name = 'annuaire/chalet_form.html'

    def get_success_url(self):
        return reverse_lazy('chalet-detail', kwargs={'pk': self.object.pk})


class ChaletDetailView(LoginRequiredMixin, DetailView):
    model = Chalet
    template_name = 'annuaire/chalet_detail.html'
    context_object_name = 'chalet'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['presences'] = PresencePSV.objects.filter(chalet=self.object).order_by('start_date')
        context['presence_form'] = PresenceForm(initial={'chalet': self.object})
        return context


class AddPresenceView(LoginRequiredMixin, CreateView):
    model = PresencePSV
    form_class = PresenceForm

    def form_valid(self, form):
        form.instance.chalet_id = self.kwargs['pk']
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('chalet-detail', kwargs={'pk': self.kwargs['pk']})

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
