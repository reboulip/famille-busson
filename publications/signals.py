from django.db import transaction
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django_q.tasks import async_task

from annuaire.file_cleanup import register_file_cleanup
from annuaire.markdown_utils import markdown_to_text
from annuaire.models import Settings as NotificationSettings
from annuaire.search.indexing import enqueue_reindex, register_search_index
from annuaire.search.registry import SearchSpec

from .models import Attachment, BlogPost
from .tasks import send_blog_post_notification

register_file_cleanup(Attachment, "file")


def _blogpost_body_and_tags(post):
    tag_names = " ".join(post.tags.values_list("name", flat=True))
    return f"{markdown_to_text(post.body)} {tag_names}"


register_search_index(
    BlogPost,
    SearchSpec(
        weights={"A": lambda p: p.title, "B": _blogpost_body_and_tags},
        source_fields=frozenset({"title", "body"}),
        accessible=lambda user: BlogPost.objects.all(),
        label="Publications",
        card_template="publications/_blogpost_card.html",
        order=["-created_at"],
    ),
)


@receiver(m2m_changed, sender=BlogPost.tags.through)
def reindex_on_tag_change(sender, instance, action, **kwargs):
    """`.tags.set()`/`.add()`/`.remove()` never fire BlogPost's own post_save, so
    the generic reindex_on wiring in register_search_index() can't see a tag
    change -- enqueue directly instead."""
    if action in {"post_add", "post_remove", "post_clear"}:
        enqueue_reindex(BlogPost, instance.pk)


@receiver(post_save, sender=BlogPost)
def notify_subscribers_of_new_post(sender, instance, created, **kwargs):
    if not created:
        return

    def _enqueue():
        # Deferred to after commit: post_save fires before form.save_m2m() adds the
        # authors, and the task re-queries the post fresh -- enqueueing before commit
        # could have it run (on a fast worker) against a row whose authors aren't
        # attached yet, or that isn't visible to the worker's own transaction at all.
        subscribers = (
            NotificationSettings.objects.filter(notify_on_new_blog_post=True)
            .exclude(person__email__isnull=True)
            .exclude(person__email="")
            .exclude(person__deceased=True)
            .select_related("person")
        )
        for subscriber in subscribers:
            async_task(send_blog_post_notification, instance.pk, subscriber.person.email)

    transaction.on_commit(_enqueue)
