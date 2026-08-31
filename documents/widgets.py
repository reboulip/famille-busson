from django import forms


class DocumentFileInput(forms.FileInput):
    """FileInput that exposes an existing file's name via a data-initial
    attribute instead of a "Currently: <a href=...>" link. DocumentStorage.url()
    always raises (documents/storage.py) -- protected document files are never
    served by a public URL -- so ClearableFileInput's default rendering, which
    calls .url to build that link, would crash the edit form for any Document
    that already has a file. document_files.js already reads data-initial as
    its fallback when building the "existing file" badge."""

    def get_context(self, name, value, attrs):
        if value and getattr(value, "name", None):
            attrs = {**(attrs or {}), "data-initial": value.name}
        return super().get_context(name, value, attrs)
