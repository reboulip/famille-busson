# Permissions — who can do what

Authorization is spread across a handful of mixins/helpers in `annuaire/views.py` and
`publications/views.py` rather than one central place. This page collects them.

## The guards

| Guard | Where | Rule |
|---|---|---|
| `LoginRequiredMixin` | Django | Must be authenticated. Baseline on almost every view. |
| `StaffRequiredMixin` | `annuaire/views.py` | Must be authenticated **and** `is_staff`. |
| `ProfileUpdateView.get_object()` | `annuaire/views.py` | Staff/superuser, or the `Person` must be the requesting user's own `profile`. |
| `_get_person_for_relations_edit()` | `annuaire/views.py` | Staff/superuser, or `person.account == request.user`. Shared by `PersonRelationsView`, `AddRelationView`, `UpdateRelationView`, `DeleteRelationView`. |
| `ChaletOwnerOrStaffMixin` | `annuaire/views.py` | Staff/superuser, or the requesting user's `profile` is in the chalet's `owners`. |
| `AuthorOrStaffRequiredMixin` | `publications/views.py` | `is_staff`, or the requesting user's `profile` is in the post's `authors`. |

All of the ownership checks (`ProfileUpdateView`, `_get_person_for_relations_edit`,
`ChaletOwnerOrStaffMixin`) raise `django.core.exceptions.PermissionDenied` directly from
`get_object()` — see `CLAUDE.md` §4's "Ownership checks go in `get_object()`" convention.

## By view

| View | Route name(s) | Guard | Effective rule |
|---|---|---|---|
| `DirectoryListView`, `ProfileDetailView`, `ChaletListView`, `ChaletDetailView`, `AddPresenceView`, `UpdatePresenceView`, `DeletePresenceView`, `ProfileCreateView` | `annuaire` | `LoginRequiredMixin` | Any logged-in user. |
| `ProfileUpdateView` | `person-edit` | `get_object()` override | Owner of the profile, or staff/superuser. |
| `PersonRelationsView` (read), `AddRelationView`, `UpdateRelationView`, `DeleteRelationView` | `person-relations-edit`, `person-relation-*` | `_get_person_for_relations_edit()` | Owner of the `Person`, or staff/superuser. `PersonRelationsView.get()` calls this helper too, so viewing the relations page is just as gated as editing it. |
| `BulkAccountCreateView`, `ChaletCreateView` | `accounts-bulk-create`, `chalet-create` | `StaffRequiredMixin` | Staff only. |
| `ChaletUpdateView`, `ChaletOwnersUpdateView` | `chalet-edit`, `chalet-owners-edit` | `ChaletOwnerOrStaffMixin` | Chalet owner, or staff/superuser. |
| `BlogPostListView`, `BlogPostDetailView` (read + comment) | `publications` | `LoginRequiredMixin` | Any logged-in user with a completed profile can comment; posting requires a `Person` profile. |
| `BlogPostCreateView` | `blogpost-create` | `LoginRequiredMixin` + `dispatch()` check | Any logged-in user with a completed profile. |
| `BlogPostUpdateView`, `BlogPostDeleteView` | `blogpost-edit`, `blogpost-delete` | `AuthorOrStaffRequiredMixin` | An author of that post, or staff. |
| `CommentDeleteView` | `comment-delete` | `StaffRequiredMixin` | **Staff only — not the comment's own author.** Asymmetric with blog post deletion, where authors can delete their own posts. |

## Superuser vs staff

The ownership `get_object()` overrides in `annuaire` (`ProfileUpdateView`,
`_get_person_for_relations_edit`, `ChaletOwnerOrStaffMixin`) treat `is_staff` and
`is_superuser` as equally privileged (`user.is_staff or user.is_superuser`).
`StaffRequiredMixin` and `AuthorOrStaffRequiredMixin` only check `is_staff` — in
practice this project always sets `is_superuser` alongside `is_staff` (see
`AccountManager.create_superuser`), so the distinction hasn't bitten yet, but a
staff-false/superuser-true account would be blocked from `BulkAccountCreateView`,
`ChaletCreateView`, `CommentDeleteView`, and editing others' blog posts.
