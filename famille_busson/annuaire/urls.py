from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    home, my_profile, edit_my_profile, check_emails_ajax,
    CustomLoginView, SignupView,
    BulkAccountCreateView, ForcedPasswordChangeView,
    DirectoryListView, ProfileDetailView, ProfileUpdateView,
    ChaletListView, ChaletDetailView,
    AddPresenceView, UpdatePresenceView, DeletePresenceView,
)

urlpatterns = [
    path('', home, name='home'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('profile/', my_profile, name='my-profile'),
    path('profile/edit', edit_my_profile, name='edit-my-profile'),
    path('accounts/bulk-create/', BulkAccountCreateView.as_view(), name='bulk-account-create'),
    path('accounts/check-emails/', check_emails_ajax, name='check-emails-ajax'),
    path('password/change/', ForcedPasswordChangeView.as_view(), name='password-change-forced'),
    path('annuaire/', DirectoryListView.as_view(), name='directory'),
    path('personne/<int:pk>/', ProfileDetailView.as_view(), name='personne-detail'),
    path('personne/<int:pk>/update', ProfileUpdateView.as_view(), name='person-edit'),
    path('chalets/', ChaletListView.as_view(), name='chalet-list'),
    path('chalets/<int:pk>/', ChaletDetailView.as_view(), name='chalet-detail'),
    path('chalets/<int:pk>/presence/ajouter/', AddPresenceView.as_view(), name='presence-add'),
    path('chalets/<int:pk>/presence/<int:presence_pk>/modifier/', UpdatePresenceView.as_view(), name='presence-edit'),
    path('chalets/<int:pk>/presence/<int:presence_pk>/supprimer/', DeletePresenceView.as_view(), name='presence-delete'),
]
