from django.contrib import admin

from .models import Event, EventGroupAccess


class EventGroupAccessInline(admin.TabularInline):
    model = EventGroupAccess
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "start", "end", "created_by")
    search_fields = ("title",)
    inlines = [EventGroupAccessInline]
