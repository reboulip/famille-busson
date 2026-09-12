"""Audit log registration -- see AuditEvent (annuaire/models.py) for the row
shape. Mirrors annuaire/file_cleanup.py's register_file_cleanup() idiom: a
model opts in by calling register_audit() once from its app's signals.py,
naming exactly which fields are worth recording (an explicit allowlist, never
"every field" by reflection -- this is what keeps password/calendar_token/
search_vector/search_text structurally out of the log)."""

from __future__ import annotations

import contextvars
from contextlib import contextmanager

from django.db import models
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save

from .middleware import get_current_actor
from .models import AuditEvent


def _stringify(value) -> str:
    if value is None:
        return ""
    return str(value)


_UNSET = object()

# Set around annuaire.anonymisation.anonymise_person()'s Person.save() so
# register_audit()'s generic per-field UPDATE never fires there -- without
# this, that UPDATE's `changes` payload would permanently store the
# pre-anonymisation PII (old name, email, ...) as the "from" value, defeating
# the erasure this same operation is trying to guarantee. The explicit
# ANONYMISE event (with no old-value payload) is the record that survives.
_suppress_generic_audit_var: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "suppress_generic_audit", default=False
)


@contextmanager
def suppress_generic_audit():
    token = _suppress_generic_audit_var.set(True)
    try:
        yield
    finally:
        _suppress_generic_audit_var.reset(token)


def record_audit_event(
    instance: models.Model, *, action: str, changes: dict | None = None, actor: object = _UNSET
) -> None:
    """Public so a change a generic post_save/post_delete pairing can't
    express (an M2M change, an erasure, a corbeille restore/purge) can still
    go through the same log -- see annuaire.person_merge/personal_data for the
    equivalent pattern on registration helpers.

    `actor` defaults to the request-scoped contextvar (annuaire.middleware's
    AuditActorMiddleware) -- pass it explicitly when logging from outside a
    request (a management command, a background task) or when the caller
    already has the acting Account in hand and shouldn't depend on ambient
    request state (see SoftDeleteModelMixin.soft_delete())."""
    from django.contrib.contenttypes.models import ContentType

    if actor is _UNSET:
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
        if _suppress_generic_audit_var.get():
            return
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
        if _suppress_generic_audit_var.get():
            return
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
        if _suppress_generic_audit_var.get():
            return
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
