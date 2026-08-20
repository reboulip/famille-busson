# Roadmap — Famille Busson

> Shipped items are moved to [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) at
> release time (see the `release-workflow` skill) — this file only ever tracks pending
> work.

## Annuaire — administration

- [x] A · Fix bulk account creation failing past ~30 accounts —
  `BulkAccountCreateView` returns an internal server error partway through large
  batches (reproduced 3x at ~30 accounts). Likely an email-send timeout or provider
  rate limit hit while sending credentials/reset emails in a loop. Investigate the
  email backend's per-request limits and make the send resilient (batching,
  async/queued sending, or per-account error isolation so one failure doesn't 500 the
  whole batch). Should land before the Notifications — abonnements item below, which
  adds more scheduled email sends. (priority: high) [#41]

---

## Annuaire — profile improvements

- [ ] A · Remove postal address from directory list cards — `annuaire_list.html` cards
  currently show profile picture, full name, and physical address; drop the address to
  make cards smaller. Address stays visible on the profile detail page. (priority:
  low) [#43]

---

## Annuaire — carte

- [ ] A · Interactive map view of member locations — new "Carte" view plotting each
  profile's address (already geocoded via the BAN address picker) on a map. Handle
  profiles with no address or an address the picker couldn't resolve. Gated behind
  authentication like every other view. (priority: medium) [#44]

---

## Généalogie — arbre interactif

- [ ] A · Interactive family tree view — new dedicated page building a genealogy graph
  from `Relation` records (parent/enfant, conjoint/conjoint), using a JS graph library
  (to be evaluated). Supports incremental exploration from a given profile and a
  full-graph overview (or overview of each disconnected component if the family graph
  isn't fully connected). Nodes show profile photo + full name; clicking a node shows
  profile details inline, with a link to the full profile page. Gated behind
  authentication like every other view. (priority: medium) [#40]

---

## Notifications — abonnements

- [ ] A · Per-profile notification subscriptions — new `Settings` model, one-to-one
  with `Person`, with opt-in checkboxes for birthday reminders (an email sent to
  subscribed users on someone's birthday) and new blog post notifications (an email
  sent to subscribed users on each new `BlogPost`). Exposed in the profile creation
  form, later in the edit form or a dedicated settings menu (to be decided during
  implementation). Depends on the Annuaire — administration bulk-email fix above
  landing first, since this adds more scheduled/bulk email sends. (priority: medium)
  [#39]
