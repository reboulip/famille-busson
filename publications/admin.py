from django.contrib import admin

from .models import Attachment, BlogPost, Comment


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    readonly_fields = ('is_image', 'uploaded_at')


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'post_type', 'created_at')
    list_filter = ('post_type',)
    search_fields = ('title', 'body')
    filter_horizontal = ('authors',)
    inlines = [AttachmentInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'created_at')
    search_fields = ('body',)


admin.site.register(Attachment)
