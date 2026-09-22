from django.db import migrations


def forwards(apps, schema_editor):
    Tag = apps.get_model("publications", "Tag")
    BlogPost = apps.get_model("publications", "BlogPost")
    # BlogPost.objects here is the historical model's plain (unfiltered) manager --
    # SoftDeleteManager isn't use_in_migrations, so this deliberately also picks up
    # soft-deleted/trashed "BC" posts, not just visible ones.
    bc_posts = list(BlogPost.objects.filter(post_type="BC"))
    if not bc_posts:
        # Don't create the tag on a fresh/empty database (every test run
        # included) if there's nothing to attach it to.
        return
    tag, _created = Tag.objects.get_or_create(name="Busson connection", defaults={"accent": "gold"})
    for post in bc_posts:
        post.tags.add(tag)


def reverse(apps, schema_editor):
    Tag = apps.get_model("publications", "Tag")
    try:
        tag = Tag.objects.get(name="Busson connection")
    except Tag.DoesNotExist:
        return
    for post in tag.posts.all():
        post.post_type = "BC"
        post.save(update_fields=["post_type"])


class Migration(migrations.Migration):
    dependencies = [
        ("publications", "0006_alter_blogpost_options_blogpost_deleted_at_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, reverse),
    ]
