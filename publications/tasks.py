"""Background-queue task wrappers (9.7).

django-q2 calls this directly by import path. Takes the post's PK and the
recipient's plain email address -- never a model instance or a built message --
so the task re-queries fresh state after the enqueueing transaction has committed
(see publications/signals.py's on_commit wrapper) rather than carrying a payload
that could go stale (or fail to serialize) between enqueue and execution.
"""

from __future__ import annotations

import logging

from annuaire import emails
from annuaire.email_utils import send_one_email

from .models import BlogPost

logger = logging.getLogger("django")


def send_blog_post_notification(post_pk: int, recipient_email: str) -> None:
    try:
        post = BlogPost.objects.get(pk=post_pk)
    except BlogPost.DoesNotExist:
        # The post was deleted between enqueue and execution -- nothing to notify
        # about, and retrying won't make it exist again.
        logger.info("send_blog_post_notification: post %s no longer exists, skipping", post_pk)
        return

    message = emails.new_blog_post(post, recipient_email)
    send_one_email(message)  # raises on failure, so django-q2 retries this recipient
