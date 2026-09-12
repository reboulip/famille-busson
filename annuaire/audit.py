"""Audit log registration -- see AuditEvent (annuaire/models.py) for the row
shape. Mirrors annuaire/file_cleanup.py's register_file_cleanup() idiom: a
model opts in by calling register_audit() once from its app's signals.py,
naming exactly which fields are worth recording (an explicit allowlist, never
"every field" by reflection -- this is what keeps password/calendar_token/
search_vector/search_text structurally out of the log)."""

from __future__ import annotations

from django.db import models
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save

from .middleware import get_current_actor
from .models import AuditEvent


def _stringify(value) -> str:
    if value is None:
        return ""
    return str(value)


def record_audit_event(instance: models.Model, *, action: str, changes: dict | None = None) -> None:
    """Public so a change a generic post_save/post_delete pairing can't
    express (an M2M change, an erasure, a corbeille restore/purge) can still
    go through the same log -- see annuaire.person_merge/personal_data for the
    equivalent pattern on registration helpers."""
    from django.contrib.contenttypes.models import ContentType

    actor = get_current_actor()
    AuditEvent.objects.create(
        content_type=ContentType.objects.get_for_model(type(instance)),
        object_id=str(instance.pk),
        object_repr=str(instance)[:200],
        action=action,
        changes=changes or {},
        actor=actor,
        actor_label=str(actor) if actor is not None else "",
    )


def register_audit(model: type[models.Model], *, fields: list[str]) -> None:
    """Records create/update/delete for `model`. `fields` is the allowlist of
    concrete field names to diff on update -- never derived by reflection."""

    def _on_pre_save(sender, instance, **kwargs):
        if instance.pk is None:
            instance._audit_old_values = None
            return
        try:
            old = model.objects.get(pk=instance.pk)
        except model.DoesNotExist:
            instance._audit_old_values = None
            return
        instance._audit_old_values = {field_name: getattr(old, field_name) for field_name in fields}

    def _on_post_save(sender, instance, created, **kwargs):
        if created:
            record_audit_event(instance, action=AuditEvent.Action.CREATE)
            return
        old_values = getattr(instance, "_audit_old_values", None)
        if old_values is None:
            return
        changes = {}
        for field_name in fields:
            old_value = old_values[field_name]
            new_value = getattr(instance, field_name)
            if old_value != new_value:
                changes[field_name] = {"from": _stringify(old_value), "to": _stringify(new_value)}
        if changes:
            record_audit_event(instance, action=AuditEvent.Action.UPDATE, changes=changes)

    def _on_post_delete(sender, instance, **kwargs):
        record_audit_event(instance, action=AuditEvent.Action.DELETE)

    pre_save.connect(_on_pre_save, sender=model, weak=False)
    post_save.connect(_on_post_save, sender=model, weak=False)
    post_delete.connect(_on_post_delete, sender=model, weak=False)


def register_m2m_membership_audit(through, *, forward_target, reverse_target) -> None:
    """Registers audit logging for a plain M2M's membership changes, in
    either direction it can be edited from. `forward_target`/`reverse_target`
    resolve the AuditEvent target instance(s) for the field-owner side and the
    related side respectively -- e.g. for Account.groups, editing from
    account.groups targets the Account directly (forward), while editing from
    group.account_set (as GroupMembersUpdateView does) targets each affected
    Account by pk (reverse). Both directions record MEMBERSHIP_ADD/REMOVE
    against the Account, never the Group -- "who gained/lost access" is what
    matters for an audit trail, not the group's own row."""

    def _on_changed(sender, instance, action, reverse, pk_set, **kwargs):
        if action not in {"post_add", "post_remove"}:
            return
        event_action = (
            AuditEvent.Action.MEMBERSHIP_ADD if action == "post_add" else AuditEvent.Action.MEMBERSHIP_REMOVE
        )
        targets = (reverse_target if reverse else forward_target)(instance, pk_set or set())
        for target, changes in targets:
            record_audit_event(target, action=event_action, changes=changes)

    m2m_changed.connect(_on_changed, sender=through, weak=False)
