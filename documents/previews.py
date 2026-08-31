import os

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
PDF_EXTENSIONS = {".pdf"}


def preview_kind(filename):
    extension = os.path.splitext(filename)[1].lower()
    if extension in IMAGE_EXTENSIONS:
        return "image"
    if extension in PDF_EXTENSIONS:
        return "pdf"
    return "other"
