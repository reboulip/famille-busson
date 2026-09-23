# Search

One search field, on every page, searches people, publications, documents, albums,
photos and life stories at the same time. This page describes how search behaves. The
code is in `annuaire/search/`.

## The search field

The search field appears in the top bar on mobile, and at the top of the side menu on
desktop. Only logged-in users see it.

A search needs **at least 2 characters**. With fewer, the results page asks the user
to type more.

## Results page

- **Default view:** results are grouped by type (people, publications, documents,
  albums, photos, stories), with up to 5 results per type. If a type has more results,
  a "Voir tout (N) →" link appears.
- **"Voir tout" view** (`?type=...`): the results of one type only, 20 per page, with a
  link back to the grouped view. If the type is unknown, the page shows "Aucun
  résultat".

Search respects access rights. A document in a locked category, or a photo in an album
the user cannot open, never appears in the results. See
[`permissions.md`](permissions.md) for the rules.

## Where the code lives

| File | What it holds |
|---|---|
| `annuaire/search/text.py` | Text cleanup: removes accents, ignores case, splits the query into words. |
| `annuaire/search/backends.py` | Two search engines: a full, ranked search for Postgres (production), and a simple one for SQLite (development). |
| `annuaire/search/registry.py` | For each searchable model: which fields are indexed, who can see what, and how a result is displayed. |
| `annuaire/search/service.py` | Runs a search across all types, or for one type. |
| `annuaire/views.py` | `GlobalSearchView`, the results page. |
| `annuaire/templates/annuaire/_search_form.html` | The search field. |
| `annuaire/templates/annuaire/search_results.html` | The results page. |

## Manual verification: ranking is Postgres-only

Only Postgres sorts results by relevance. The tests run on SQLite, so they check
*which* results come back, not their order. In development (SQLite), results are
sorted by a fixed order, such as newest first.

To check the ranking, test by hand on a Postgres database. Search for a word that
appears in the title of one item and only in the body of another. The item with the
word in its title should come first.
