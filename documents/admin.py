from django.contrib import admin

from .models import Category, CategoryGroupAccess, Document, DocumentFile


class CategoryGroupAccessInline(admin.TabularInline):
    model = CategoryGroupAccess
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent")
    search_fields = ("name",)
    inlines = [CategoryGroupAccessInline]


class DocumentFileInline(admin.TabularInline):
    model = DocumentFile
    extra = 0
    readonly_fields = ("extraction_status", "uploaded_at")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "document_date", "redactor", "created_at")
    list_filter = ("category",)
    search_fields = ("title", "description")
    inlines = [DocumentFileInline]
