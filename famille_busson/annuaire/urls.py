from django.urls import path
import django.contrib.auth.views as auth_views
from .views import home, profil, VueDetailProfil

urlpatterns = [
    path('', home, name='accueil'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('profil/', profil, name='profil'),
    path('personne/<int:pk>/', VueDetailProfil.as_view(), name='personne-detail'),
]
