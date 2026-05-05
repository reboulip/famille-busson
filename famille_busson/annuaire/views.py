from django.db.models.base import Model as Model
from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.contrib import messages
from django.views.generic import DetailView, UpdateView, FormView
from django.urls import reverse_lazy
from django.http import HttpResponseForbidden
from .models import Personne, Compte, Relation
from .forms import FormEditionProfil, FormSetEditionRelations, CustomAuthenticationForm, SignupForm

def home(request):
    return render(request, 'annuaire/home.html')


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
        print(user)

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
            raise HttpResponseForbidden("Adresse email non reconnue, vous ne pouvez pas créer de compte.")
        elif Compte.objects.filter(email=email).exists():
            messages.error(self.request, "Un compte avec cet email existe déjà.")
            return redirect('custom_login')
        else:
            user = Compte.objects.create_user(email=email)
            user.set_password(password)
            user.save()

            login(self.request, user)
            return super().form_valid(form)
        

class VueDetailProfil(LoginRequiredMixin, DetailView):
    model = Personne
    template_name = 'annuaire/personne_detail.html'
    context_object_name = 'personne'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        personne = self.get_object()

        # Récupérer le partenaire (mariage ou conjoint)
        partenaire_relation = Relation.objects.filter(
            Q(personne1=personne) | Q(personne2=personne),
            nature_relation__in=[0, 1]
        ).first()
        if partenaire_relation:
            # Identifier le partenaire
            if partenaire_relation.personne1 == personne:
                partenaire = partenaire_relation.personne2
            else:
                partenaire = partenaire_relation.personne1
            context['partenaire'] = partenaire
            context['partenaire_type'] = partenaire_relation.get_nature_relation_display()

        # Récupérer les parents
        parents_relations = Relation.objects.filter(
            personne1=personne,
            nature_relation=2
        )
        parents = [rel.personne2 for rel in parents_relations]
        context['parents'] = parents

        # Récupérer les enfants
        enfants_relations = Relation.objects.filter(
            personne1=personne,
            nature_relation=3
        )
        enfants = [rel.personne2 for rel in enfants_relations]
        context['enfants'] = enfants
        
        print(context)
        return context


class VueEditionProfil(LoginRequiredMixin, UpdateView):
    model = Personne
    form_class = FormEditionProfil
    template_name = 'annuaire/update_form.html'
    success_url = reverse_lazy('my-profile')

    def get_object(self, queryset=None) -> Model:
        obj = super().get_object(queryset=queryset)
        profil = self.request.user.profil
        if obj != profil:
            raise HttpResponseForbidden("Vous ne pouvez pas éditer ce profil car ce n'est pas le vôtre.")
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
        print(f'{form_relations.is_valid()=}')
        if form_relations.is_valid():
            form_relations.instance = self.object
            form_relations.save()
        else:
            for form_rel in form_relations:
                print(form_rel.cleaned_data)
                print(form_rel.errors)
            return super(VueEditionProfil, self).form_invalid(form)
        return super(VueEditionProfil, self).form_valid(form)