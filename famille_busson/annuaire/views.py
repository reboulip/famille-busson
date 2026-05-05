from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.views.generic import DetailView, UpdateView, FormView, ListView, CreateView, DeleteView
from django.urls import reverse_lazy
from .models import Personne, Compte, Relation, Chalet, PresencePSV
from .forms import FormEditionProfil, FormSetEditionRelations, CustomAuthenticationForm, SignupForm, FormPresencePSV


def home(request):
    personnes_recentes = Personne.objects.all().order_by('-pk')[:6]
    return render(request, 'annuaire/home.html', {'personnes_recentes': personnes_recentes})


@login_required
def my_profile(request):
    try:
        personne = Personne.objects.get(compte=request.user)
        return redirect('personne-detail', pk=personne.pk)
    except Personne.DoesNotExist:
        return render(request, 'annuaire/no_profile.html')


@login_required
def edit_my_profile(request):
    try:
        personne = Personne.objects.get(compte=request.user)
        return redirect('personne-edition', pk=personne.pk)
    except Personne.DoesNotExist:
        return render(request, 'annuaire/no_profile.html')


class CustomLoginView(LoginView):
    template_name = 'annuaire/login.html'
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        if hasattr(user, 'profil'):
            login(self.request, user)
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, "Aucun profil associé à cet utilisateur.")
            return redirect('login')

    def get_success_url(self):
        return reverse_lazy('accueil')


class SignupView(FormView):
    template_name = 'annuaire/signup.html'
    form_class = SignupForm
    success_url = reverse_lazy('edit-my-profile')

    def form_valid(self, form):
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')

        if not Personne.objects.filter(email=email).exists():
            messages.error(self.request, "Adresse email non reconnue, vous ne pouvez pas créer de compte.")
            return self.form_invalid(form)
        elif Compte.objects.filter(email=email).exists():
            messages.error(self.request, "Un compte avec cet email existe déjà.")
            return redirect('login')
        else:
            user = Compte.objects.create_user(email=email)
            user.set_password(password)
            user.save()
            login(self.request, user)
            return super().form_valid(form)


class VueListeAnnuaire(LoginRequiredMixin, ListView):
    model = Personne
    template_name = 'annuaire/annuaire_list.html'
    context_object_name = 'personnes'

    def get_queryset(self):
        q = self.request.GET.get('q', '')
        qs = Personne.objects.all().order_by('nom', 'prenom')
        if q:
            qs = qs.filter(Q(nom__icontains=q) | Q(prenom__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


class VueDetailProfil(LoginRequiredMixin, DetailView):
    model = Personne
    template_name = 'annuaire/personne_detail.html'
    context_object_name = 'personne'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        personne = self.get_object()

        partenaire_relation = Relation.objects.filter(
            Q(personne1=personne) | Q(personne2=personne),
            nature_relation__in=[0, 1]
        ).first()
        if partenaire_relation:
            if partenaire_relation.personne1 == personne:
                partenaire = partenaire_relation.personne2
            else:
                partenaire = partenaire_relation.personne1
            context['partenaire'] = partenaire
            context['partenaire_type'] = partenaire_relation.get_nature_relation_display()

        parents_relations = Relation.objects.filter(personne1=personne, nature_relation=2)
        context['parents'] = [rel.personne2 for rel in parents_relations]

        enfants_relations = Relation.objects.filter(personne1=personne, nature_relation=3)
        context['enfants'] = [rel.personne2 for rel in enfants_relations]

        return context


class VueEditionProfil(LoginRequiredMixin, UpdateView):
    model = Personne
    form_class = FormEditionProfil
    template_name = 'annuaire/update_form.html'
    success_url = reverse_lazy('my-profile')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        if obj != self.request.user.profil:
            raise PermissionDenied("Vous ne pouvez pas éditer ce profil car ce n'est pas le vôtre.")
        return obj

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['formsets'] = [FormSetEditionRelations(self.request.POST, instance=self.object)]
        else:
            data['formsets'] = [FormSetEditionRelations(instance=self.object)]
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


class VueListeChalets(LoginRequiredMixin, ListView):
    model = Chalet
    template_name = 'annuaire/chalet_list.html'
    context_object_name = 'chalets'


class VueDetailChalet(LoginRequiredMixin, DetailView):
    model = Chalet
    template_name = 'annuaire/chalet_detail.html'
    context_object_name = 'chalet'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['presences'] = PresencePSV.objects.filter(chalet=self.object).order_by('date_debut')
        context['form_presence'] = FormPresencePSV(initial={'chalet': self.object})
        return context


class VueAjouterPresence(LoginRequiredMixin, CreateView):
    model = PresencePSV
    form_class = FormPresencePSV

    def form_valid(self, form):
        form.instance.chalet_id = self.kwargs['pk']
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('chalet-detail', kwargs={'pk': self.kwargs['pk']})

    def form_invalid(self, form):
        messages.error(self.request, "Erreur dans le formulaire de présence.")
        return redirect('chalet-detail', pk=self.kwargs['pk'])


class VueModifierPresence(LoginRequiredMixin, UpdateView):
    model = PresencePSV
    form_class = FormPresencePSV
    template_name = 'annuaire/presence_form.html'
    pk_url_kwarg = 'presence_pk'

    def get_success_url(self):
        return reverse_lazy('chalet-detail', kwargs={'pk': self.kwargs['pk']})


class VueSupprimerPresence(LoginRequiredMixin, DeleteView):
    model = PresencePSV
    pk_url_kwarg = 'presence_pk'

    def get(self, request, *args, **kwargs):
        return redirect('chalet-detail', pk=self.kwargs['pk'])

    def get_success_url(self):
        return reverse_lazy('chalet-detail', kwargs={'pk': self.kwargs['pk']})
