from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    home, my_profile, edit_my_profile,
    CustomLoginView, SignupView,
    VueListeAnnuaire, VueDetailProfil, VueEditionProfil,
    VueListeChalets, VueDetailChalet,
    VueAjouterPresence, VueModifierPresence, VueSupprimerPresence,
)

urlpatterns = [
    path('', home, name='accueil'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('profile/', my_profile, name='my-profile'),
    path('profile/edit', edit_my_profile, name='edit-my-profile'),
    path('annuaire/', VueListeAnnuaire.as_view(), name='annuaire'),
    path('personne/<int:pk>/', VueDetailProfil.as_view(), name='personne-detail'),
    path('personne/<int:pk>/update', VueEditionProfil.as_view(), name='personne-edition'),
    path('chalets/', VueListeChalets.as_view(), name='chalet-list'),
    path('chalets/<int:pk>/', VueDetailChalet.as_view(), name='chalet-detail'),
    path('chalets/<int:pk>/presence/ajouter/', VueAjouterPresence.as_view(), name='presence-ajouter'),
    path('chalets/<int:pk>/presence/<int:presence_pk>/modifier/', VueModifierPresence.as_view(), name='presence-modifier'),
    path('chalets/<int:pk>/presence/<int:presence_pk>/supprimer/', VueSupprimerPresence.as_view(), name='presence-supprimer'),
]
