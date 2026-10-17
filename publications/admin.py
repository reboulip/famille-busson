from django.contrib import admin

from .models import Attachment, BlogPost, Bulletin, BulletinGroupAccess, BulletinImage, BulletinImport, Comment, Tag


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    readonly_fields = ("is_image", "uploaded_at")


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at")
    list_filter = ("tags",)
    search_fields = ("title", "body")
    filter_horizontal = ("authors", "tags")
    inlines = [AttachmentInline]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "accent")
    search_fields = ("name",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "created_at")
    search_fields = ("body",)


admin.site.register(Attachment)


class BulletinImageInline(admin.TabularInline):
    model = BulletinImage
    extra = 0
    readonly_fields = ("image_id", "kind", "width", "height", "sha256")


class BulletinGroupAccessInline(admin.TabularInline):
    model = BulletinGroupAccess
    extra = 0


@admin.register(Bulletin)
class BulletinAdmin(admin.ModelAdmin):
    list_display = ("title", "document_id", "sort_date", "status")
    list_filter = ("status", "series_code")
    search_fields = ("title", "document_id", "summary")
    inlines = [BulletinGroupAccessInline, BulletinImageInline]

    def get_queryset(self, request):
        return Bulletin.all_objects.all()


@admin.register(BulletinImport)
class BulletinImportAdmin(admin.ModelAdmin):
    list_display = ("__str__", "status", "uploaded_by", "uploaded_at")
    list_filter = ("status",)
    readonly_fields = ("uploaded_by", "uploaded_at", "document_id", "validation_report", "data")
