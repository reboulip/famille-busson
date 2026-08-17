from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Field, ManyToManyField, Model

DOC_APP_LABELS = ["annuaire", "publications"]

MERMAID_CARDINALITY = {
    "OneToOneField": "||--o|",
    "ForeignKey": "||--o{",
    "ManyToManyField": "}o--o{",
}
# For FK/O2O, the field lives on the "many"/dependent side but points at the
# "one" side, so the diagram row must list the target first (one target row
# relates to many owning-model rows) — only M2M is direction-agnostic.
TARGET_FIRST = {"OneToOneField", "ForeignKey"}


def get_output_path() -> Path:
    # Resolved at call time (not import time) so tests can override
    # settings.BASE_DIR and write to a tmp_path instead of the tracked file.
    return Path(settings.BASE_DIR) / "docs" / "data_model.md"


def describe_field(field: Field) -> str:
    notes = []
    if field.primary_key:
        notes.append("PK")

    if field.is_relation:
        target = field.related_model.__name__
        if isinstance(field, ManyToManyField):
            notes.append(f"→ {target} (M2M)")
        else:
            on_delete = field.remote_field.on_delete.__name__
            notes.append(f"→ {target} (on_delete={on_delete})")
        related_name = field.remote_field.related_name
        if related_name:
            notes.append(f"related_name='{related_name}'")
    elif getattr(field, "max_length", None):
        notes.append(f"max_length={field.max_length}")

    if getattr(field, "unique", False) and not field.primary_key:
        notes.append("unique")

    if field.choices:
        choices = ", ".join(f"{value}={label}" for value, label in field.choices)
        notes.append(f"choices: {choices}")

    if getattr(field, "auto_now_add", False):
        notes.append("auto_now_add")
    elif getattr(field, "auto_now", False):
        notes.append("auto_now")
    elif field.has_default():
        default_repr = field.default.__name__ if callable(field.default) else repr(field.default)
        notes.append(f"default={default_repr}")

    if not field.primary_key and not isinstance(field, ManyToManyField):
        notes.append("optional" if field.blank else "required")

    return ", ".join(notes)


def model_fields(model: type[Model]) -> list[Field]:
    return list(model._meta.fields) + list(model._meta.many_to_many)


def render_mermaid(models: list[type[Model]]) -> str:
    lines = ["```mermaid", "erDiagram"]
    for model in models:
        for field in model_fields(model):
            if not field.is_relation or field.related_model is None:
                continue
            internal_type = field.get_internal_type()
            cardinality = MERMAID_CARDINALITY.get(internal_type, "||--o{")
            owner, target = model.__name__, field.related_model.__name__
            left, right = (target, owner) if internal_type in TARGET_FIRST else (owner, target)
            lines.append(f'    {left} {cardinality} {right} : "{field.name}"')
    lines.append("```")
    return "\n".join(lines)


def render_model_section(model: type[Model]) -> str:
    meta = model._meta
    lines = [
        f"### `{model.__name__}`",
        "",
        f"*App:* `{meta.app_label}` · *verbose name:* {meta.verbose_name} / {meta.verbose_name_plural}"
        f" · *table:* `{meta.db_table}`",
        "",
        "| Field | Type | Verbose name | Notes |",
        "|---|---|---|---|",
    ]
    for field in model_fields(model):
        lines.append(
            f"| `{field.name}` | {field.get_internal_type()} | {field.verbose_name} | {describe_field(field)} |"
        )
    return "\n".join(lines)


class Command(BaseCommand):
    help = (
        "Regenerate docs/data_model.md from the current model definitions "
        f"({', '.join(DOC_APP_LABELS)} apps). Run after any models.py change."
    )

    def handle(self, *args, **options) -> None:
        all_models: list[type[Model]] = []
        sections = []
        for label in DOC_APP_LABELS:
            models = list(apps.get_app_config(label).get_models())
            all_models.extend(models)
            sections.append(f"## `{label}`\n\n" + "\n\n".join(render_model_section(m) for m in models))

        content = (
            "\n\n".join(
                [
                    "# Data model",
                    (
                        "> **Auto-generated — do not edit by hand.**\n"
                        "> Regenerate with `uv run python manage.py generate_data_model_docs` "
                        "after any change to `models.py` in `annuaire` or `publications`."
                    ),
                    "## Entity-relationship diagram",
                    render_mermaid(all_models),
                    *sections,
                ]
            )
            + "\n"
        )

        output_path = get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Wrote {output_path}"))
