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
| `ProfileUpdateView.get_object()` | `annuaire/views.py` | Staff/superuser, or the `Person` must be the requesting user's own `profile`. |
| `_get_person_for_relations_edit()` | `annuaire/views.py` | Staff/superuser, or `person.account == request.user`. Shared by `PersonRelationsView`, `AddRelationView`, `UpdateRelationView`, `DeleteRelationView`. |
| `ChaletOwnerOrStaffMixin` | `annuaire/views.py` | Staff/superuser, or the requesting user's `profile` is in the chalet's `owners`. |
| `AuthorOrStaffRequiredMixin` | `publications/views.py` | `is_staff`, or the requesting user's `profile` is in the post's `authors`. |

`ProfileUpdateView` and `ChaletOwnerOrStaffMixin` raise
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
| `DirectoryListView`, `ProfileDetailView`, `ChaletListView`, `ChaletDetailView`, `AddPresenceView`, `UpdatePresenceView`, `DeletePresenceView`, `ProfileCreateView`, `MapListView` | `annuaire` | `LoginRequiredMixin` | Any logged-in user. |
| `ProfileUpdateView` | `person-edit` | `get_object()` override | Owner of the profile, or staff/superuser. |
| `PersonRelationsView` (read), `AddRelationView`, `UpdateRelationView`, `DeleteRelationView` | `person-relations-edit`, `person-relation-*` | `_get_person_for_relations_edit()` | Owner of the `Person`, or staff/superuser. `PersonRelationsView.get()` calls this helper too, so viewing the relations page is just as gated as editing it. |
| `BulkAccountCreateView`, `ChaletCreateView` | `bulk-account-create`, `chalet-create` | `StaffRequiredMixin` | Staff only. |
| `ChaletUpdateView`, `ChaletOwnersUpdateView` | `chalet-edit`, `chalet-owners-edit` | `ChaletOwnerOrStaffMixin` | Chalet owner, or staff/superuser. |
| `BlogPostListView`, `BlogPostDetailView` (read + comment) | `publications` | `LoginRequiredMixin` | Any logged-in user with a completed profile can comment; posting requires a `Person` profile. |
| `BlogPostCreateView` | `blogpost-create` | `LoginRequiredMixin` + `dispatch()` check | Any logged-in user with a completed profile. |
| `BlogPostUpdateView`, `BlogPostDeleteView` | `blogpost-edit`, `blogpost-delete` | `AuthorOrStaffRequiredMixin` | An author of that post, or staff. |
| `CommentDeleteView` | `comment-delete` | `StaffRequiredMixin` | **Staff only — not the comment's own author.** Asymmetric with blog post deletion, where authors can delete their own posts. |

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

## Superuser vs staff

The ownership checks in `annuaire` (`ProfileUpdateView.get_object()`,
`_get_person_for_relations_edit()`, `ChaletOwnerOrStaffMixin.get_object()`) treat
`is_staff` and `is_superuser` as equally privileged (`user.is_staff or
user.is_superuser`).
`StaffRequiredMixin` and `AuthorOrStaffRequiredMixin` only check `is_staff` — in
practice this project always sets `is_superuser` alongside `is_staff` (see
`AccountManager.create_superuser`), so the distinction hasn't bitten yet, but a
staff-false/superuser-true account would be blocked from `BulkAccountCreateView`,
`ChaletCreateView`, `CommentDeleteView`, and editing others' blog posts.
