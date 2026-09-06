# Permissions — who can do what

Authorization is spread across a handful of mixins/helpers in `annuaire/views.py` and
`publications/views.py` rather than one central place. This page collects them.

**Every view is login-required by default.** `django.contrib.auth.middleware.LoginRequiredMiddleware`
(`famille_busson/settings.py`'s `MIDDLEWARE`, after `AuthenticationMiddleware`)
redirects any anonymous request to a view that hasn't explicitly opted out. A view
must carry `@login_not_required` (function views) or
`@method_decorator(login_not_required, name="dispatch")` (class-based views) to
stay public — see the "Public (unauthenticated) surface" section below for the
full, deliberate list. This inverts the old implicit default: a new view that
forgets both `@login_required`/`LoginRequiredMixin` **and** `@login_not_required`
now fails closed (login-required) instead of silently becoming public, which is
what let SEC-B's bug (`home` unauthenticated) happen in the first place.

## The guards

| Guard | Where | Rule |
|---|---|---|
| `LoginRequiredMixin` | Django | Must be authenticated. Baseline on almost every view. |
| `StaffRequiredMixin` | `annuaire/views.py` | Must be authenticated **and** `is_staff`. |
| `can_edit_person()` | `annuaire/views.py` | Staff/superuser; the `Person`'s own linked `Account`; or an owner (`Person.owners`) of a `Person` that has **no** linked `Account` — owner rights evaporate the instant the profile gets one (`account_id is None` is checked live, not cached). Used by `ProfileDetailView` (its `can_edit` context flag), `ProfileUpdateView.get_object()`, `PersonOwnersUpdateView.get_object()`, and `_get_person_for_relations_edit()`. |
| `_get_person_for_relations_edit()` | `annuaire/views.py` | Delegates to `can_edit_person()`. Shared by `PersonRelationsView`, `AddRelationView`, `UpdateRelationView`, `DeleteRelationView`. |
| `ChaletOwnerOrStaffMixin` | `annuaire/views.py` | Staff/superuser, or the requesting user's `profile` is in the chalet's `owners`. |
| `AuthorOrStaffRequiredMixin` | `publications/views.py` | `is_staff`, or the requesting user's `profile` is in the post's `authors`. |

`ProfileUpdateView`, `PersonOwnersUpdateView` and `ChaletOwnerOrStaffMixin` raise
`django.core.exceptions.PermissionDenied` directly from `get_object()` — see
`CLAUDE.md` §4's "Ownership checks go in `get_object()`" convention.
`_get_person_for_relations_edit()` doesn't follow that convention: it's a plain
module-level function, called from `get()`/`post()` on `PersonRelationsView`,
`AddRelationView`, `UpdateRelationView` and `DeleteRelationView` — none of which define
a `get_object()` — but it raises the same `PermissionDenied` and gates the same way.

## By view

| View | Route name(s) | Guard | Effective rule |
|---|---|---|---|
| `home` | `home` | `@login_required` | Any logged-in user. |
| `markdown_preview` | `markdown-preview` | `@login_required` + `@require_POST` | Any logged-in user. Sanitized-HTML preview endpoint for Markdown fields (`text` POST param, 400 above `MAX_MARKDOWN_LENGTH`). |
| `DirectoryListView`, `ProfileDetailView`, `ChaletListView`, `ChaletDetailView`, `AddPresenceView`, `UpdatePresenceView`, `DeletePresenceView`, `MapListView`, `FamilyTreeView`, `FamilyTreeExportView` | `annuaire` | `LoginRequiredMixin` | Any logged-in user. |
| `ChaletCreateView` | `chalet-create` | `LoginRequiredMixin` + `dispatch()` check | Any logged-in user with a completed profile; the creator is auto-added as an owner. |
| `ProfileCreateView` | `profile-create` | `LoginRequiredMixin` + `dispatch()` check | Any logged-in user with **no** linked profile yet (redirects to `my-profile` otherwise). Passes `user` to `ProfileEditForm`, so its `deceased`/`death_date` fields are staff/superuser-only — popped from the form entirely for anyone else. Same for `PersonCreateView`/`ProfileUpdateView` below. |
| `PersonCreateView` | `person-create` | `LoginRequiredMixin` + `dispatch()` check | Any logged-in user with a completed profile; creates an accountless `Person` and auto-adds the creator as an owner. Same `ProfileEditForm` field-level gate as `ProfileCreateView` above: `deceased`/`death_date` are staff/superuser-only. |
| `ProfileUpdateView` | `person-edit` | `get_object()` override (`can_edit_person()`) | Owner of the profile, or staff/superuser. Also renders and saves the profile's notification preferences (`FormSettings`) alongside the main form — no separate guard, so anyone who can edit the profile can edit its notification prefs too. Same `ProfileEditForm` field-level gate as `ProfileCreateView`/`PersonCreateView`: `deceased`/`death_date` are staff/superuser-only. |
| `PersonOwnersUpdateView` | `person-owners-edit` | `get_object()` override (`can_edit_person()` + `account_id is None`) | Owner of an **accountless** `Person`, or staff/superuser. 403 if the profile already has an `Account` — ownership stops being editable once someone can log in as that profile. |
| `ProfileClaimView` | `profile-claim` | `LoginRequiredMixin` + `dispatch()` check | Any logged-in user with **no** linked profile; self-service, instant, no approval — links the account to any `Person` with `account__isnull=True`. Deliberately not reachable from the public signup form (see "Public (unauthenticated) surface" below). |
| `PersonRelationsView` (read), `AddRelationView`, `UpdateRelationView`, `DeleteRelationView` | `person-relations-edit`, `person-relation-*` | `_get_person_for_relations_edit()` | Owner of the `Person` (via `can_edit_person()`), or staff/superuser. `PersonRelationsView.get()` calls this helper too, so viewing the relations page is just as gated as editing it. |
| `BulkAccountCreateView` | `bulk-account-create` | `StaffRequiredMixin` | Staff only. |
| `GroupListView`, `GroupCreateView`, `GroupUpdateView`, `GroupDeleteView`, `GroupMembersUpdateView` | `group-list`, `group-create`, `group-edit`, `group-delete`, `group-members-edit` | `StaffRequiredMixin` | Staff only. Membership is assigned by picking `Person`s who have an `Account` (`GroupMembersUpdateView` saves via `group.account_set.set(...)`). Deletion is guarded: `documents.CategoryGroupAccess.group` is `on_delete=PROTECT`, so deleting a `Group` still restricting a `documents.Category` raises `ProtectedError`, caught by `GroupDeleteView.post()` and shown as a French error naming the blocking categories; the confirm page also proactively disables the delete button and shows the same warning when it already knows the group is blocked. |
| `ChaletUpdateView`, `ChaletOwnersUpdateView` | `chalet-edit`, `chalet-owners-edit` | `ChaletOwnerOrStaffMixin` | Chalet owner, or staff/superuser. |
| `BlogPostListView`, `BlogPostDetailView` (read + comment) | `publications` | `LoginRequiredMixin` | Any logged-in user with a completed profile can comment; posting requires a `Person` profile. `BlogPostDetailView`'s `linked_documents` context is `accessible_documents(request.user)` filtered to the post, re-checked at render time rather than a stored snapshot — a document later moved into a locked category silently disappears from the publication page, consistent with `DocumentDetailView`'s "invisible, not locked" rule for documents (unlike `CategoryListView`'s categories). |
| `BlogPostCreateView` | `blogpost-create` | `LoginRequiredMixin` + `dispatch()` check | Any logged-in user with a completed profile. `BlogPostForm`'s `documents` field queryset is `accessible_documents(user)`; the view must pass `user` in `get_form_kwargs()` or the field silently falls back to `Document.objects.none()` (fail closed, never every document). |
| `BlogPostUpdateView`, `BlogPostDeleteView` | `blogpost-edit`, `blogpost-delete` | `AuthorOrStaffRequiredMixin` | An author of that post, or staff. `BlogPostUpdateView` has its own `get_form_kwargs()` passing `user` for the same reason as `BlogPostCreateView` — without it, the `documents` M2M field would validate against an empty queryset and silently clear every document linked to the post on save. |
| `CommentDeleteView` | `comment-delete` | `StaffRequiredMixin` | **Staff only — not the comment's own author.** Asymmetric with blog post deletion, where authors can delete their own posts. |
| `CategoryListView` | `category-list` | `LoginRequiredMixin` | Any logged-in user. **"Visible but locked":** queries `Category.objects.all()` unfiltered — every category appears, including ones the viewer can't open, which render name-only with a lock badge naming the unlocking group(s) (`documents.access.user_can_access_category()`/`effective_groups()` per row via the `documents_extras` template filters). Never uses `accessible_categories()` — that would hide locked categories entirely, which is the opposite of this project's chosen model. |
| `CategoryDetailView` | `category-detail` | `LoginRequiredMixin` | Any logged-in user; resolves via plain `get_object_or_404` (no `PermissionDenied` — the page itself isn't secret). Renders full description + document list only if `user_can_access_category()` is true; otherwise a locked placeholder naming the unlocking group(s), with no description/document leakage. |
| `DocumentListView` | `document-list` | `LoginRequiredMixin` | Any logged-in user. Uses `documents.access.accessible_documents()` — a locked category's documents never appear here regardless of direct-link guesses; the category filter dropdown is likewise populated from `accessible_categories()` only, and the redactor/year filter options are likewise derived from the accessible queryset rather than every `Person`/`document_date` in the table. Sorting (`DOCUMENT_SORTS`, mirroring the annuaire directory's sort pattern) applies after that same scoping, so no sort option can surface a locked document. |
| `document_search_ajax` | `document-search-ajax` | `@login_required` | Any logged-in user. Backs the document picker on the publication form (reuses `annuaire`'s `_person_picker.html`/`person_picker.js` unmodified, driven by `data-search-url`). Queryset is `accessible_documents(request.user)` — same access boundary as `DocumentListView`, never `Document.objects.all()`. No results below a 2-character query. |
| `CategoryCreateView`, `CategoryUpdateView`, `CategoryDeleteView` | `category-create`, `category-edit`, `category-delete` | `StaffRequiredMixin` | Staff only. `CategoryForm.clean()` re-derives the group-restriction ancestor/descendant invariant (see `documents/models.py`'s `validate_category_group_restriction` `m2m_changed` receiver) so a violating submission surfaces as a normal form error, not a 500. Deletion follows the same `ProtectedError`-catching pattern as `GroupDeleteView` (`Category.parent`/`Document.category` are both `on_delete=PROTECT`), showing document/child-category counts and disabling the delete button when non-empty. |
| `DocumentFileView` | `document-file`, `document-file-thumbnail` | `LoginRequiredMixin` + explicit `user_can_access_category()` check | Any logged-in user who can access the file's `Document.category` (re-checked on every request, independent of any list/detail filtering — the only way to reach a `DocumentFile`'s bytes, since `DocumentStorage.url()` raises). Keyed by `DocumentFile` pk only, never by path. `@xframe_options_sameorigin` (not the site's default `DENY`) — originally so a same-origin PDF `<embed>` could render; PDFs now render via `pdf.js` canvas instead (see `document_viewer.js`), which doesn't need it, but the decorator hasn't been removed. Inline `Content-Disposition` only for `.png/.jpg/.jpeg/.gif/.webp/.pdf`, `attachment` otherwise or when `?download=1`; `X-Content-Type-Options: nosniff` always. Thumbnail variant 404s if the `DocumentFile` has none. |
| `DocumentDetailView` | `document-detail` | `LoginRequiredMixin` | Any logged-in user. Queryset scoped to `accessible_documents()` — a document in a locked category 404s directly (unlike categories, documents are never "visible but locked"). `can_edit` context flag (for the edit/delete buttons) is true for staff/superuser or the document's own `uploaded_by`. |
| `DocumentCreateView` | `document-create` | `LoginRequiredMixin` + `dispatch()` profile check | Any logged-in user with a completed profile (redirects to `profile-create` otherwise, mirroring `BlogPostCreateView`). The category `<select>` is scoped to `accessible_categories(user)` for non-staff — a member can never even see a locked category as an upload target; staff/superuser get every category. Sets `Document.uploaded_by` to the requester's profile. |
| `DocumentUpdateView`, `DocumentDeleteView` | `document-edit`, `document-delete` | `UploaderOrStaffRequiredMixin` | The document's own `uploaded_by`, or staff/superuser (`user.is_staff or user.is_superuser`, not `is_staff`-only — deliberately not copying `AuthorOrStaffRequiredMixin`'s documented bug). Ownership check in `get_object()`, raising `PermissionDenied`, per this project's standard convention. |

## Public (unauthenticated) surface

Every view is gated except: `login` (`CustomLoginView`), `signup` (`SignupView`),
`logout`, `healthz` (`famille_busson/urls.py`), `password_reset_confirm`
(`AccountPasswordResetConfirmView` — must be reachable by a signed-out user
following an emailed link), `password-reset` (`AccountPasswordResetView`) and
`password-reset-done` (`AccountPasswordResetDoneView`) — the self-service "mot de
passe oublié" request form linked from the login page and its "check your email"
confirmation, both of which follow Django's stock no-user-enumeration behavior:
requesting a reset for an unregistered email still redirects to the confirmation
page without sending anything or revealing whether the account exists. `healthz`
and the root `/` redirect (`famille_busson/urls.py`) are also public, each
decorated `@login_not_required`. `home` was the last unauthenticated view in
`annuaire`/`publications` until it was gated; nothing new should be added to this
list without a deliberate decision — and since `LoginRequiredMiddleware` now fails
closed, a new view that's meant to be public won't work at all until it's
explicitly decorated and added here.

Django's own auth views (`LoginView`, `PasswordResetView`,
`PasswordResetDoneView`, `PasswordResetConfirmView`) already carry
`login_not_required` in Django 5.1+, so `CustomLoginView` and this project's three
`AccountPasswordReset*` subclasses inherit the exemption automatically — they are
not separately decorated in `annuaire/views.py`. `SignupView` has no such
built-in exemption and is decorated explicitly. Django's `LogoutView` is used
directly (no project subclass) and is **not** decorated — an anonymous `GET` to
`/logout/` bounces to login, which is harmless since only an authenticated user
ever sees a logout control.

`/media/<path>` is now gated too, via `media_serve`
(`annuaire/views.py`, wired in `famille_busson/urls.py`) — an `@login_required`
wrapper around `django.views.static.serve` so uploaded files
(`Person.profile_photo`, `Chalet.photo`, blog `Attachment.file`) are no longer
readable by anyone who obtains the URL.

`password_reset_confirm` is additionally listed in
`ForcePasswordChangeMiddleware.EXEMPT_URL_PREFIXES`
(`annuaire/middleware.py`) — an already-authenticated user flagged
`must_change_password` must still be able to follow their own reset link instead
of being bounced to `/password/change/`.

The passwordless "magic link" login flow (reachable from the login page) adds four
more public routes. `magic-link-request` (`MagicLinkRequestView`, a `PasswordResetView`
subclass reusing Django's stock `PasswordResetForm` unmodified) and `magic-link-sent`
(`MagicLinkSentView`, a `PasswordResetDoneView` subclass) inherit `login_not_required`
automatically, the same as the `AccountPasswordReset*` views above. `magic-link-confirm-token`
(the emailed link itself) and `magic-link-confirm` (the "confirm your login" button page)
are both served by `MagicLinkConfirmView`, a plain `View` — not a Django auth-view
subclass, so it has no built-in exemption to inherit and is decorated explicitly with
`@method_decorator(login_not_required, name="dispatch")`. `ForcePasswordChangeMiddleware.
EXEMPT_URL_PREFIXES` also lists `/annuaire/login/magic/`, for the same reason as
`password_reset_confirm`: an already-authenticated user flagged `must_change_password`
must still be able to complete the magic-link flow instead of being bounced to
`/password/change/`.

## Superuser vs staff

The ownership checks in `annuaire` (`ProfileUpdateView.get_object()`,
`PersonOwnersUpdateView.get_object()`, `_get_person_for_relations_edit()`,
`ChaletOwnerOrStaffMixin.get_object()`) treat `is_staff` and `is_superuser` as equally
privileged (`user.is_staff or user.is_superuser`).
`StaffRequiredMixin` and `AuthorOrStaffRequiredMixin` only check `is_staff` — in
practice this project always sets `is_superuser` alongside `is_staff` (see
`AccountManager.create_superuser`), so the distinction hasn't bitten yet, but a
staff-false/superuser-true account would be blocked from `BulkAccountCreateView`,
`CommentDeleteView`, and editing others' blog posts.
