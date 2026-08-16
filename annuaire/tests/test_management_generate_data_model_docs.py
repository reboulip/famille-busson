from io import StringIO

from django.core.management import call_command

from annuaire.management.commands.generate_data_model_docs import OUTPUT_PATH


def run_generate():
    out = StringIO()
    call_command('generate_data_model_docs', stdout=out)
    return out.getvalue()


class TestGenerateDataModelDocs:
    def test_writes_output_file(self):
        output = run_generate()
        assert 'Wrote' in output
        assert OUTPUT_PATH.exists()

    def test_content_covers_every_model(self):
        run_generate()
        content = OUTPUT_PATH.read_text(encoding='utf-8')
        assert 'erDiagram' in content
        for model_name in (
            'Account', 'Person', 'Relation', 'Chalet', 'PresencePSV',
            'BlogPost', 'Attachment', 'Comment',
        ):
            assert f'### `{model_name}`' in content

    def test_foreign_key_diagram_row_lists_target_on_the_one_side(self):
        run_generate()
        content = OUTPUT_PATH.read_text(encoding='utf-8')
        assert 'Person ||--o{ Relation : "person1"' in content
