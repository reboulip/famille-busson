from io import StringIO

import pytest
from django.core.management import call_command

from annuaire.management.commands.generate_data_model_docs import get_output_path


@pytest.fixture(autouse=True)
def tmp_base_dir(tmp_path, settings):
    """Redirect the generated docs file to a temp dir so tests never touch
    the real, git-tracked docs/data_model.md."""
    settings.BASE_DIR = tmp_path


def run_generate() -> str:
    out = StringIO()
    call_command("generate_data_model_docs", stdout=out)
    return out.getvalue()


class TestGenerateDataModelDocs:
    def test_writes_output_file(self):
        output = run_generate()
        assert "Wrote" in output
        assert get_output_path().exists()

    def test_content_covers_every_model(self):
        run_generate()
        content = get_output_path().read_text(encoding="utf-8")
        assert "erDiagram" in content
        for model_name in (
            "Account",
            "Person",
            "Relation",
            "Chalet",
            "PresencePSV",
            "BlogPost",
            "Attachment",
            "Comment",
        ):
            assert f"### `{model_name}`" in content

    def test_foreign_key_diagram_row_lists_target_on_the_one_side(self):
        run_generate()
        content = get_output_path().read_text(encoding="utf-8")
        assert 'Person ||--o{ Relation : "person1"' in content
