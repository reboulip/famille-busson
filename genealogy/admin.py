from django.contrib import admin

from .models import Citation, Source, Story, StoryPhoto


class StoryPhotoInline(admin.TabularInline):
    model = StoryPhoto
    extra = 0


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ["title", "person", "date", "created_by"]
    search_fields = ["title", "person__first_name", "person__last_name"]
    inlines = [StoryPhotoInline]


class CitationInline(admin.TabularInline):
    model = Citation
    extra = 0


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "date", "created_by"]
    search_fields = ["title", "reference", "repository"]
    inlines = [CitationInline]


@admin.register(Citation)
class CitationAdmin(admin.ModelAdmin):
    list_display = ["source", "story", "person", "relation", "claim"]
    search_fields = ["source__title", "note"]
