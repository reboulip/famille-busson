from django.contrib.auth.models import Group
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .audit import register_audit, register_m2m_membership_audit
from .file_cleanup import register_file_cleanup
from .markdown_utils import markdown_to_text
from .models import Account, Chalet, Person, Relation, Settings, SiteConfig
from .search.indexing import register_search_index
from .search.registry import SearchSpec
from .site_config import CACHE_KEY as SITE_CONFIG_CACHE_KEY

register_file_cleanup(Person, "profile_photo")
register_file_cleanup(Chalet, "photo")

register_search_index(
    Person,
    SearchSpec(
        weights={
            "A": lambda p: f"{p.first_name} {p.last_name}",
            "B": lambda p: markdown_to_text(p.description),
        },
        # email/phone_number/postal_address are deliberately excluded: they're
        # already visible on the profile, but making them *searchable* enables
        # reverse lookup by phone/address, a materially different exposure.
        source_fields=frozenset({"first_name", "last_name", "description"}),
        accessible=lambda user: Person.objects.all(),
        label="Personnes",
        card_template="annuaire/_person_card.html",
        order=["last_name", "first_name"],
    ),
)


@receiver(post_save, sender=Account)
def link_account_to_person(sender, instance, created, **kwargs):
    if created:
        # Person.email is not unique -- an accountless profile's email can collide
        # with another Person's (e.g. a parent reusing their own address while
        # creating a child's profile), so .get() would raise MultipleObjectsReturned.
        # Prefer the oldest still-accountless match; only that one can plausibly be
        # "the" account-less profile this new Account represents.
        person = Person.objects.filter(email=instance.email, account__isnull=True).order_by("pk").first()
        if person is not None:
            person.account = instance
            person.save()
            person.owners.clear()


@receiver(post_save, sender=Person)
def create_settings_for_person(sender, instance, created, **kwargs):
    if created:
        Settings.objects.get_or_create(person=instance)


@receiver(post_save, sender=SiteConfig)
def invalidate_site_config_cache(sender, instance, **kwargs):
    cache.delete(SITE_CONFIG_CACHE_KEY)


@receiver(post_save, sender=Relation)
def create_inverse_relation(sender, instance: Relation, created, **kwargs):
    person1 = instance.person1
    person2 = instance.person2
    relationship_type = instance.relationship_type
    is_spouse = relationship_type in [0, 1]
    inverse_type = relationship_type if is_spouse else 5 - relationship_type
    # start_date/marriage_place/end_date are spouse-only facts, identical on both
    # mirrored rows; nulled/blanked on a parent/child row.
    inverse_start_date = instance.start_date if is_spouse else None
    inverse_marriage_place = instance.marriage_place if is_spouse else ""
    inverse_end_date = instance.end_date if is_spouse else None
    try:
        inverse = Relation.objects.get(person1=person2, person2=person1)
        if (
            inverse.relationship_type != inverse_type
            or inverse.start_date != inverse_start_date
            or inverse.marriage_place != inverse_marriage_place
            or inverse.end_date != inverse_end_date
        ):
            inverse.relationship_type = inverse_type
            inverse.start_date = inverse_start_date
            inverse.marriage_place = inverse_marriage_place
            inverse.end_date = inverse_end_date
            inverse.save()
    except Relation.DoesNotExist:
        inverse = Relation.objects.create(
            person1=person2,
            person2=person1,
            relationship_type=inverse_type,
            start_date=inverse_start_date,
            marriage_place=inverse_marriage_place,
            end_date=inverse_end_date,
        )
        inverse.save()


@receiver(post_delete, sender=Relation)
def delete_inverse_relation(sender, instance: Relation, **kwargs):
    Relation.objects.filter(person1=instance.person2, person2=instance.person1).delete()


# --- Audit log (14.4) -- registered last, after every other receiver above,
# so a save/delete this module already reacts to is fully settled before the
# corresponding audit row is written. ------------------------------------

register_audit(
    Person,
    fields=[
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "postal_address",
        "latitude",
        "longitude",
        "birth_date",
        "birth_place",
        "deceased",
        "death_date",
        "death_place",
        "description",
        "export_privacy",
    ],
)
register_audit(
    Relation, fields=["person1_id", "person2_id", "relationship_type", "start_date", "marriage_place", "end_date"]
)
register_audit(
    SiteConfig,
    fields=[
        "site_name",
        "wordmark",
        "tagline",
        "sender_address",
        "feedback_url",
        "timezone",
        "default_language",
    ],
)


def _account_groups_forward_target(instance, pk_set):
    # instance: Account whose own .groups changed. pk_set: Group pks.
    if not pk_set:
        return []
    names = list(Group.objects.filter(pk__in=pk_set).values_list("name", flat=True))
    return [(instance, {"groupes": {"to": ", ".join(names)}})]


def _account_groups_reverse_target(instance, pk_set):
    # instance: Group edited via its reverse account_set accessor (see
    # GroupMembersUpdateView.post(), which uses group.account_set.set(...)).
    # pk_set: Account pks whose membership in this group changed.
    if not pk_set:
        return []
    group_name = instance.name
    return [(account, {"groupes": {"to": group_name}}) for account in Account.objects.filter(pk__in=pk_set)]


register_m2m_membership_audit(
    Account.groups.through,
    forward_target=_account_groups_forward_target,
    reverse_target=_account_groups_reverse_target,
)


def _person_owners_forward_target(instance, pk_set):
    # instance: the Person whose .owners changed. pk_set: owner Person pks.
    if not pk_set:
        return []
    names = [str(p) for p in Person.objects.filter(pk__in=pk_set)]
    return [(instance, {"proprietaires": {"to": ", ".join(names)}})]


def _person_owners_reverse_target(instance, pk_set):
    # instance: the owner, edited via its reverse .managed_profiles accessor.
    # pk_set: the managed Person pks whose .owners set changed.
    if not pk_set:
        return []
    owner_name = str(instance)
    return [(person, {"proprietaires": {"to": owner_name}}) for person in Person.objects.filter(pk__in=pk_set)]


register_m2m_membership_audit(
    Person.owners.through,
    forward_target=_person_owners_forward_target,
    reverse_target=_person_owners_reverse_target,
)
