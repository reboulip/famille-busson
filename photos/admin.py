from django.contrib import admin

from .models import Album, AlbumGroupAccess, Photo


class AlbumGroupAccessInline(admin.TabularInline):
    model = AlbumGroupAccess
    extra = 0


class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 0
    readonly_fields = ("derivative_status", "uploaded_at")
    fk_name = "album"


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "created_at")
    search_fields = ("title",)
    inlines = [AlbumGroupAccessInline, PhotoInline]


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("__str__", "album", "uploaded_by", "derivative_status", "uploaded_at")
    list_filter = ("derivative_status", "album")
    search_fields = ("caption",)
