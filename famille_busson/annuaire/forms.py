from django import forms
from .models import Person, Relation, Account, PresencePSV
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, password_validation


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ['first_name', 'last_name', 'profile_photo', 'email', 'phone_number', 'postal_address', 'birth_date', 'description']


RelationEditFormSet = forms.inlineformset_factory(Person, Relation, fk_name='person1', extra=1,
                                                  fields=['person2', 'relationship_type', 'start_date'])


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

    def get_user(self) -> Account:
        email = self.cleaned_data.get('username')
        account = Account.objects.get(email=email)
        return account


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
        if Account.objects.filter(email=email).exists():
            raise forms.ValidationError("Un compte avec cet email existe déjà.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        email = self.cleaned_data.get('email')
        password_validation.validate_password(password, email)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm:
            if password != password_confirm:
                raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return cleaned_data


class PresenceForm(forms.ModelForm):
    class Meta:
        model = PresencePSV
        fields = ['person', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
