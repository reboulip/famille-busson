from django.db.models.signals import pre_save
from django.dispatch import receiver

from annuaire.file_cleanup import register_file_cleanup
from annuaire.markdown_utils import markdown_to_text
from annuaire.search.indexing import register_search_index
from annuaire.search.registry import SearchSpec

from .access import accessible_documents
from .models import Document, DocumentFile


def _document_body(document):
    # Folds in every child DocumentFile's OCR text -- reindex_on=[(DocumentFile,
    # "document")] below re-derives this from scratch on every file save/delete,
    # so a deleted scan's text is never left stranded in the parent's index.
    parts = [markdown_to_text(document.description)]
    parts += list(document.files.values_list("extracted_text", flat=True))
    return " ".join(part for part in parts if part)


register_search_index(
    Document,
    SearchSpec(
        weights={"A": lambda d: d.title, "B": _document_body},
        source_fields=frozenset({"title", "description"}),
        accessible=accessible_documents,
        label="Documents",
        card_template="documents/_document_card.html",
        order=["-created_at"],
    ),
    reindex_on=[(DocumentFile, "document")],
)


@receiver(pre_save, sender=DocumentFile)
def reset_extraction_on_file_change(sender, instance, **kwargs):
    """Replacing a file must invalidate whatever was extracted from the old
    one -- otherwise a replaced scan stays searchable by its old content, an
    access-control-adjacent leak, not just staleness. Connected before
    register_file_cleanup() below so its own pre_save handler sees the
    thumbnail already cleared here and schedules the old thumbnail file for
    deletion too (signal receivers on the same sender fire in connection
    order)."""
    if instance.pk is None:
        return
    try:
        old = DocumentFile.objects.get(pk=instance.pk)
    except DocumentFile.DoesNotExist:
        return
    if old.file.name != instance.file.name:
        instance.extraction_status = "pending"
        instance.extracted_text = ""
        instance.extraction_error = ""
        instance.extracted_at = None
        instance.ocr_used = False
        instance.thumbnail = None


register_file_cleanup(DocumentFile, "file", "thumbnail")
