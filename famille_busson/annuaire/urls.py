from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import home, profil, VueDetailProfil, VueEditionProfil, CustomLoginView, SignupView

urlpatterns = [
    path('', home, name='accueil'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('profil/', profil, name='profil'),
    path('personne/<int:pk>/', VueDetailProfil.as_view(), name='personne-detail'),
    path('personne/<int:pk>/update', VueEditionProfil.as_view(), name='personne-edition'),
]
