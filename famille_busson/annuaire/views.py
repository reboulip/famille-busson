from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from .models import Personne

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