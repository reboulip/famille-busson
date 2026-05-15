from django.contrib import admin
from .models import Person, Account, Relation, Chalet, PresencePSV


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email')


admin.site.register(Account)
admin.site.register(Relation)
admin.site.register(Chalet)
admin.site.register(PresencePSV)
