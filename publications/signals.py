from annuaire.file_cleanup import register_file_cleanup

from .models import Attachment

register_file_cleanup(Attachment, "file")
