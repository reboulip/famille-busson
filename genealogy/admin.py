from django.contrib import admin

from .models import Story, StoryPhoto


class StoryPhotoInline(admin.TabularInline):
    model = StoryPhoto
    extra = 0


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ["title", "person", "date", "created_by"]
    search_fields = ["title", "person__first_name", "person__last_name"]
    inlines = [StoryPhotoInline]
