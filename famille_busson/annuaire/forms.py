from django import forms
from .models import Personne, Relation

class FormEditionProfil(forms.ModelForm):
    class Meta:
        model = Personne
        fields = ['prenom', 'nom', 'photo_profil', 'email', 'numero_telephone', 'adresse_postale', 'date_naissance', 'description']


FormSetEditionRelations = forms.inlineformset_factory(Personne, Relation, fk_name='personne1', extra=1,
                                                      fields=['personne2', 'nature_relation', 'date_debut'])
