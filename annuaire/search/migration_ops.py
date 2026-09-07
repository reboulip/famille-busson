from django.db import migrations


def create_gin_index_operation(index_name: str, table_name: str, column: str = "search_vector"):
    """A vendor-guarded RunPython creating a GIN index on Postgres only.

    Never declare this via Meta.indexes/GinIndex: SQLite recreates every index from
    model state on `_remake_table` (triggered by any future AlterField on the model),
    and GinIndex.create_sql unconditionally emits "USING gin" -- invalid SQL outside
    Postgres. A vendor-guarded RunPython is the only representation safe on both
    backends. The vendor check happens INSIDE the callable, at migration execution
    time, never at module import time.
    """

    def _create(apps, schema_editor):
        if schema_editor.connection.vendor != "postgresql":
            return
        schema_editor.execute(f'CREATE INDEX IF NOT EXISTS "{index_name}" ON "{table_name}" USING GIN ("{column}")')

    def _drop(apps, schema_editor):
        if schema_editor.connection.vendor != "postgresql":
            return
        schema_editor.execute(f'DROP INDEX IF EXISTS "{index_name}"')

    return migrations.RunPython(_create, _drop)
