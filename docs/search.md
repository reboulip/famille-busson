# Search

One search field, reachable from anywhere on the site, searching across people,
publications, documents, albums and photos at once. Built on the shared backend
abstraction from `annuaire/search/` (see "Where the code lives" below) — this page
covers the user-facing behaviour; the indexing/backend internals are covered in code
comments in that package.

## The search field

`annuaire/templates/annuaire/_search_form.html` is mounted **twice** in
`base.html`: once in `.fb-topbar` (mobile) and once at the top of the desktop
`.fb-sidebar`'s nav — the two are never visible at the same time, so both need their
own mount rather than sharing one. Each mount gets its own `input_id` (no duplicate DOM
ids). Only shown to authenticated users (`{% if user.is_authenticated %}`).

Submitting the form (`GET`, `?q=`) goes to `search` (`/annuaire/recherche/`),
`GlobalSearchView`. The field itself carries `minlength="2"` as a client-side hint; the
view enforces the same **2-character minimum** server-side
(`MIN_SEARCH_QUERY_LENGTH` in `annuaire/views.py`) — below that, the results page
renders a "keep typing" prompt rather than querying anything.

## Results page

`annuaire/templates/annuaire/search_results.html`, rendered by `GlobalSearchView`:

- **No `?type=`** — a grouped preview: up to 5 results per registered type
  (`Person`, `BlogPost`, `Document`, `Album`, `Photo`), each type in its own section
  with its own card partial. A type with more results than shown gets a
  "Voir tout (N) →" link.
- **`?type=<key>`** (e.g. `annuaire.person`, `documents.document`) — the "Voir tout"
  target: that one type only, paginated 20 per page (`django.core.paginator.Paginator`),
  with a link back to the grouped view. `key` is the `SearchSpec`'s registered model,
  as `"<app_label>.<model_name>"` (`annuaire.search.service.model_key`); an
  unrecognized or stale `key` (e.g. a hand-edited URL after a type was removed) renders
  the "Aucun résultat" empty state rather than erroring — it doesn't fall back to the
  grouped view.

Every group/type is built from that model's own `SearchSpec.accessible(user)` queryset,
never `Model.objects.all()` — a document in a locked category, or a photo in an
album the viewer isn't in the group for, never appears, in either the preview or the
expanded list. See [`permissions.md`](permissions.md)'s `GlobalSearchView` row for the
exact access rule per type.

## Where the code lives

| File | What it holds |
|---|---|
| `annuaire/search/text.py` | `normalize()` (accent-folding, casefold, whitespace collapse), `terms()` (splits a query into safe `\w+` word runs — what keeps the raw Postgres tsquery injection-safe). |
| `annuaire/search/backends.py` | `PostgresSearchBackend` (ranked, prefix-matching full-text search, French config), `FallbackSearchBackend` (`icontains` AND, SQLite/dev — no ranking possible), `get_search_backend()` dispatching on `connection.vendor`. |
| `annuaire/search/registry.py` | `SearchSpec` — one per searchable model: which fields feed the index (`weights`), the access-filter callable, the result label, and the card template. |
| `annuaire/search/service.py` | `search_all(user, query, per_type_limit)` (the grouped preview) and `search_one(user, query, key)` (one type, for the `?type=` expansion). |
| `annuaire/views.py` | `GlobalSearchView`. |
| `annuaire/templates/annuaire/_search_form.html` | The shared search field partial. |
| `annuaire/templates/annuaire/search_results.html` | The results page (grouped or expanded). |

## Manual verification: ranking is Postgres-only

There is no Postgres CI leg this sprint, so ranked ordering can't be asserted by the
automated test suite — tests exercise `FallbackSearchBackend` (SQLite) and assert
result *membership*, never order (see `FallbackSearchBackend`'s docstring). In dev
(SQLite), results within a type are returned in `SearchSpec.order` order (e.g. most
recent first), not relevance order — a plain "does this text appear anywhere in the
indexed fields" match. Verify ranked ordering by hand against a Postgres database
(e.g. via `docker compose`) before relying on relevance order in production: search for
a term that appears at different weights across several rows (e.g. once in a title,
once only in a body) and confirm the title hit ranks first.
