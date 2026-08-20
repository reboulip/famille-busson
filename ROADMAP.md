# Roadmap — Famille Busson

> Shipped items are moved to [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) at
> release time (see the `release-workflow` skill) — this file only ever tracks pending
> work.

## Généalogie — arbre interactif

- [x] A · Interactive family tree view — new dedicated page building a genealogy graph
  from `Relation` records (parent/enfant, conjoint/conjoint), using a JS graph library
  (to be evaluated). Supports incremental exploration from a given profile and a
  full-graph overview (or overview of each disconnected component if the family graph
  isn't fully connected). Nodes show profile photo + full name; clicking a node shows
  profile details inline, with a link to the full profile page. Gated behind
  authentication like every other view. (priority: medium) [#40]
