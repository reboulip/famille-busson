from django import forms
from django.contrib.auth.models import User
from .models import Personne, Relation, Compte
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, password_validation

class FormEditionProfil(forms.ModelForm):
    class Meta:
        model = Personne
        fields = ['prenom', 'nom', 'photo_profil', 'email', 'numero_telephone', 'adresse_postale', 'date_naissance', 'description']


FormSetEditionRelations = forms.inlineformset_factory(Personne, Relation, fk_name='personne1', extra=1,
                                                      fields=['personne2', 'nature_relation', 'date_debut'])


class CustomAuthenticationForm(AuthenticationForm):
    password = forms.CharField(label='Mot de passe', strip=False, widget=forms.PasswordInput)

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(self.request, email=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError("Email ou mot de passe incorrect.")
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data
    
    def get_user(self) -> User:
        email = self.cleaned_data.get('username')
        compte = Compte.objects.get(email=email)
        return compte


class SignupForm(forms.Form):
    email = forms.EmailField(label='Email')
    password = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={'placeholder': 'Ton mot de passe'}),
        strip=False,
    )
    password_confirm = forms.CharField(
        label='Confirmez le mot de passe',
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirme ton mot de passe'}),
        strip=False,
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Compte.objects.filter(email=email).exists():
            raise forms.ValidationError("Un compte avec cet email existe déjà.")
        return email
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        # Valideurs de mots de passe de Django
        password_validation.validate_password(password, self.instance)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm:
            if password != password_confirm:
                raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return cleaned_data