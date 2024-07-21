from django.contrib import admin
from .models import Personne, Compte, Relation, Chalet, PresencePSV

@admin.register(Personne)
class PersonneAdmin(admin.ModelAdmin):
    list_display = ('prenom', 'nom', 'email')

admin.site.register(Compte)
admin.site.register(Relation)
admin.site.register(Chalet)
admin.site.register(PresencePSV)
