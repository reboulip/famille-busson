from django.db.models.base import Model as Model
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, UpdateView
from django.urls import reverse_lazy
from django.http import HttpResponseForbidden
from .models import Personne
from .forms import FormEditionProfil, FormSetEditionRelations


def home(request):
    return render(request, 'annuaire/home.html')


@login_required
def profil(request):
    try:
        personne = Personne.objects.get(compte=request.user)
        return redirect('personne-detail', pk=personne.pk)
    except Personne.DoesNotExist:
        return render(request, 'annuaire/no_profile.html')
    

class VueDetailProfil(LoginRequiredMixin, DetailView):
    model = Personne
    template_name = 'annuaire/personne_detail.html'
    context_object_name = 'personne'


class VueEditionProfil(LoginRequiredMixin, UpdateView):
    model = Personne
    form_class = FormEditionProfil
    template_name = 'annuaire/update_form.html'
    success_url = reverse_lazy('profil')

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