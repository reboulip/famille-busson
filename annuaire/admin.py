from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Person, Account, Relation, Chalet, PresencePSV


@admin.register(Account)
class AccountAdmin(UserAdmin):
    ordering = ('email',)
    list_display = ('email', 'is_staff', 'is_active', 'must_change_password')
    search_fields = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'must_change_password', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'must_change_password'),
        }),
    )


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email')


admin.site.register(Relation)
admin.site.register(Chalet)
admin.site.register(PresencePSV)
