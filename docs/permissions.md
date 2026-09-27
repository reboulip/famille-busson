# Permissions — who can do what

Access rules are spread across several helpers in the apps' `views.py` files. This
page collects them in one place.

**Every page requires login by default.** Django's `LoginRequiredMiddleware` sends
anonymous visitors to the login page. To make a page public, you must mark it
explicitly with `@login_not_required` (or
`@method_decorator(login_not_required, name="dispatch")` for class-based views). So if
you forget to protect a new page, it stays protected. The list of public pages is in
"Public (unauthenticated) surface" below.

## The guards

| Guard | Where | Rule |
|---|---|---|
| `LoginRequiredMixin` | Django | Must be logged in. Used on almost every page. |
| `StaffRequiredMixin` | `annuaire/views.py` | Must be logged in **and** staff. |
| `can_edit_person()` | `annuaire/views.py` | Staff; the person themself; or an "owner" of a profile that has **no** account (for example, a parent for a child's profile). Owners lose their rights as soon as the profile gets its own account. |
| `_get_person_for_relations_edit()` | `annuaire/views.py` | Same rule as `can_edit_person()`, for the family relations pages. |
| `PlaceOwnerOrStaffMixin` | `annuaire/views.py` | Staff, or an owner of the place. |
| `AuthorOrStaffRequiredMixin` | `publications/views.py` | Staff, or an author of the post. |
| `EventOrganiserOrStaffMixin` | `events/views.py` | Staff, or an organiser of the event. |
| `StoryOwnerOrStaffRequiredMixin` | `genealogy/views.py` | Staff, or the author of the story. |

Most ownership checks happen in the view's `get_object()`, which raises
`PermissionDenied` (HTTP 403). The relations pages have no `get_object()`, so they call
`_get_person_for_relations_edit()` from `get()` and `post()` instead. The result is the
same.

## By view

"Completed profile" means the user's account is linked to a profile (`Person`).

| View | Route name(s) | Guard | Effective rule |
|---|---|---|---|
| `home` | `home` | `@login_required` | Any logged-in user. The "Il y a X ans" photos and the upcoming events only show what the user is allowed to see. |
| `markdown_preview` | `markdown-preview` | `@login_required` + POST only | Any logged-in user. Shows a preview of Markdown text. |
| `GlobalSearchView` | `search` | `LoginRequiredMixin` | Any logged-in user. Results only include what the user can see: no documents from locked categories, no photos from restricted albums. See [`search.md`](search.md). |
| `ActivityFeedView` | `activity-feed` | `LoginRequiredMixin` | Any logged-in user. Same access rules as search. |
| `CalendarView` | `calendrier` | `LoginRequiredMixin` | Any logged-in user. Shows events (only those the user can see), stays in houses, and birthdays (not for deceased people). |
| `calendar_feed_ajax` | `calendar-feed-ajax` | `@login_required` | Any logged-in user. Loads more calendar data when the user changes month. Same rules as above. |
| `regenerate_calendar_token` | `regenerate-calendar-token` | `@login_required` + POST only | Any logged-in user, for their **own** calendar link. The old `.ics` link stops working at once. |
| `DirectoryListView`, `ProfileDetailView`, `PlaceListView`, `PlaceDetailView`, `AddStayView`, `UpdateStayView`, `DeleteStayView`, `FamilyTreeView`, `FamilyTreeExportView` | `annuaire` | `LoginRequiredMixin` | Any logged-in user. On a profile, the "Photos" tab only shows photos from albums the user can open, and the photo count only counts those. The "Histoire" tab shows the person's life stories, and hides photos from restricted albums. The Excel export of the family tree only hides people whose privacy choice is "redact". |
| `MapListView` | `carte` | `LoginRequiredMixin` | Any logged-in user. All people and houses appear. Events only appear if the user can see them and they have an address with coordinates. |
| `PlaceCreateView` | `place-create` | `LoginRequiredMixin` + profile check | Any logged-in user with a completed profile. The creator becomes an owner. |
| `ProfileCreateView` | `profile-create` | `LoginRequiredMixin` + profile check | A logged-in user who has **no** profile yet. Only staff can fill in the death fields (`deceased`, `death_date`, `death_place`). Anyone who can edit the profile can set its export privacy choice. |
| `PersonCreateView` | `person-create` | `LoginRequiredMixin` + profile check | Any logged-in user with a completed profile. Creates a profile with no account; the creator becomes an owner. Same field rules as `ProfileCreateView`. |
| `ProfileUpdateView` | `person-edit` | `can_edit_person()` | See `can_edit_person()`. Also edits the person's email notification settings. Same field rules as `ProfileCreateView`. |
| `PersonOwnersUpdateView` | `person-owners-edit` | `can_edit_person()` + no account | An owner or staff, only for a profile with **no** account. Returns 403 once the profile has an account. |
| `PersonAnonymiseView` | `person-anonymise` | `StaffRequiredMixin` | Staff only. Erases a person's identity for good. See [`privacy.md`](privacy.md#retention-and-erasure-policy). |
| `PersonalDataExportView` | `person-data-export` | `can_edit_person()` | Same as `person-edit`. Downloads a `.zip` of the person's data. It only includes what the **requesting user** can see. See [`privacy.md`](privacy.md). |
| `ProfileClaimView` | `profile-claim` | `LoginRequiredMixin` + profile check | A logged-in user with no profile. Links their account to an existing profile that has no account. Instant, with no approval. Not available from the public signup form. |
| `PersonRelationsView`, `AddRelationView`, `UpdateRelationView`, `DeleteRelationView` | `person-relations-edit`, `person-relation-*` | `_get_person_for_relations_edit()` | See `can_edit_person()`. Even viewing the relations page needs this right. |
| `BulkAccountCreateView` | `bulk-account-create` | `StaffRequiredMixin` | Staff only. |
| `PersonDuplicateListView` | `person-duplicate-list` | `StaffRequiredMixin` | Staff only. Lists profiles that may be duplicates (same name, same surname and birth date, or same email). |
| `PersonMergeView` | `person-merge` | `StaffRequiredMixin` | Staff only. Merges two profiles: everything linked to one profile moves to the other. Staff choose which value to keep for each differing field. Refused if both profiles have an account. |
| `GedcomImportUploadView`, `GedcomImportReviewView`, `GedcomImportApplyView`, `GedcomImportDiscardView` | `gedcom-import-*` | `StaffRequiredMixin` | Staff only. Import a GEDCOM family tree file: upload, review each person (create, merge or skip), then apply or discard. Nothing changes before "apply". Accepts UTF-8 and CP1252 files. |
| `AuditLogListView` | `audit-log-list` | `StaffRequiredMixin` | Staff only. See [`audit.md`](audit.md). |
| `CorbeilleListView` | `corbeille-list` | `StaffRequiredMixin` | Staff only. Lists items in the trash. See [`corbeille.md`](corbeille.md). |
| `CorbeilleRestoreView`, `CorbeillePurgeView` | `corbeille-restore`, `corbeille-purge` | `StaffRequiredMixin` + POST only | Staff only. Restore an item, or delete it for good. Only the four trash-enabled models are accepted (404 otherwise). |
| `SiteConfigUpdateView` | `site-config` | `StaffRequiredMixin` | Staff only. Edits the site settings. See [`site_config.md`](site_config.md). |
| `GroupListView`, `GroupCreateView`, `GroupUpdateView`, `GroupDeleteView`, `GroupMembersUpdateView` | `group-*` | `StaffRequiredMixin` | Staff only. A group that still restricts a document category, an album or an event cannot be deleted. The page says which ones block it. |
| `PlaceUpdateView`, `PlaceOwnersUpdateView` | `place-edit`, `place-owners-edit` | `PlaceOwnerOrStaffMixin` | An owner of the place, or staff. |
| `BlogPostListView`, `BlogPostDetailView` | `publications` | `LoginRequiredMixin` | Any logged-in user can read. A completed profile is needed to comment. Documents and albums linked to a post only appear if the user can see them. |
| `BlogPostCreateView` | `blogpost-create` | `LoginRequiredMixin` + profile check | Any logged-in user with a completed profile. The user can only link documents and albums they can see. |
| `BlogPostUpdateView`, `BlogPostDeleteView` | `blogpost-edit`, `blogpost-delete` | `AuthorOrStaffRequiredMixin` | An author of the post, or staff. |
| `CommentDeleteView` | `comment-delete` | `StaffRequiredMixin` | **Staff only. The author of a comment cannot delete it.** This is different from posts, which their authors can delete. |
| `CategoryListView` | `category-list` | `LoginRequiredMixin` | Any logged-in user. **"Visible but locked":** all categories are listed. A category the user cannot open shows only its name, a lock, and the group(s) that can open it. |
| `CategoryDetailView` | `category-detail` | `LoginRequiredMixin` | Any logged-in user. If the user cannot open the category, the page shows a lock and the group(s) that can open it, with no description or documents. |
| `DocumentListView` | `document-list` | `LoginRequiredMixin` | Any logged-in user. Only lists documents the user can see. The filters and sorting only use those documents too. |
| `document_search_ajax` | `document-search-ajax` | `@login_required` | Any logged-in user. Searches documents for the document picker (in the post form). Only returns documents the user can see. Needs at least 2 characters. Up to 20 results. |
| `CategoryCreateView`, `CategoryUpdateView`, `CategoryDeleteView` | `category-*` | `StaffRequiredMixin` | Staff only. A category that still contains documents or sub-categories cannot be deleted. |
| `DocumentFileView` | `document-file`, `document-file-thumbnail` | `LoginRequiredMixin` + category access check | A logged-in user who can open the document's category. This is the **only** way to download a document file. Access is checked on every request. Images and PDFs open in the browser. Other files are downloaded. |
| `DocumentDetailView` | `document-detail` | `LoginRequiredMixin` | Any logged-in user who can see the document. Otherwise 404: unlike categories, documents are never "visible but locked". The uploader and staff can edit. |
| `DocumentCreateView` | `document-create` | `LoginRequiredMixin` + profile check | Any logged-in user with a completed profile. Members can only upload into categories they can open. Staff can upload anywhere. |
| `DocumentUpdateView`, `DocumentDeleteView` | `document-edit`, `document-delete` | `UploaderOrStaffRequiredMixin` | The uploader, or staff. |
| `AlbumListView` | `album-list` | `LoginRequiredMixin` | Any logged-in user. **"Visible but locked"**, like categories: all albums are listed, and locked ones show only their name, a lock, and the group(s) that can open them. |
| `AlbumCreateView` | `album-create` | `LoginRequiredMixin` + profile check | Any logged-in user with a completed profile. |
| `AlbumDetailView` | `album-detail` | `LoginRequiredMixin` | Any logged-in user. If the user cannot open the album, the page shows a lock, with no description or photos. The creator and staff can edit. |
| `PhotoUploadView` | `photo-upload` | `LoginRequiredMixin` + album access check | Any member who can open the album. |
| `PhotoTagView` | `photo-tag` | `LoginRequiredMixin` + album access check | Any member who can open the album can say who is in a photo. This is open to everyone on purpose: recognising people in old photos is a group effort. |
| `PhotoDetailView` | `photo-detail` | `LoginRequiredMixin` | Any logged-in user who can open the album. Otherwise 404: photos are never "visible but locked". The uploader and staff can edit. |
| `PhotoUpdateView`, `PhotoDeleteView` | `photo-edit`, `photo-delete` | `PhotoOwnerOrStaffRequiredMixin` | The uploader, or staff. Only the caption can be edited. |
| `AlbumUpdateView`, `AlbumDeleteView` | `album-edit`, `album-delete` | `AlbumOwnerOrStaffRequiredMixin` | The creator, or staff. Deleting an album moves it to the trash (see [`corbeille.md`](corbeille.md)). |
| `PhotoFileView` | `photo-file`, `photo-file-web`, `photo-file-thumbnail` | `LoginRequiredMixin` + album access check | A logged-in user who can open the album. This is the **only** way to get a photo file. Access is checked on every request. Browsers may cache files, but shared proxies may not. If the thumbnail is not ready yet, the original photo is sent. |
| `album_search_ajax` | `album-search-ajax` | `@login_required` | Any logged-in user. Searches albums for the album picker (in the post form). Only returns albums the user can see. Needs at least 2 characters. Up to 10 results. |
| `EventListView`, `EventDetailView` | `event-list`, `event-detail` | `LoginRequiredMixin` | Any logged-in user. A restricted event is **invisible** to non-members (404), never "visible but locked": a date and an address are more sensitive than a folder name. By default the list shows upcoming events; `?passes=1` shows past events. Organisers and staff can edit. |
| `EventCreateView` | `event-create` | `LoginRequiredMixin` + profile check | Any logged-in user with a completed profile. The creator always becomes an organiser. |
| `EventUpdateView`, `EventDeleteView` | `event-edit`, `event-delete` | `EventOrganiserOrStaffMixin` | An organiser, or staff. |
| `EventRsvpView` | `event-rsvp` | `LoginRequiredMixin` + `can_edit_person()` | A member who can see the event can answer for themself, or for a profile they own (for example, a parent for a child). |
| `GedcomExportView` | `gedcom-export` | `LoginRequiredMixin` | Any logged-in user. Exports the family tree as a GEDCOM file. Living people's names are hidden, unless they chose to share them. A person counts as living if they are under 100, or if their birth date is unknown. |
| `StoryCreateView` | `story-create` | `LoginRequiredMixin` | Any logged-in user can add a story to any profile. |
| `StoryUpdateView`, `StoryDeleteView` | `story-update`, `story-delete` | `StoryOwnerOrStaffRequiredMixin` | The story's author, or staff. |

Sources and citations (`genealogy.Source`, `genealogy.Citation`) have no pages in the
site. Staff manage them in the Django admin.

## Public (unauthenticated) surface

These pages work without login:

- **Login and signup:** `login`, `signup`, `logout`.
- **Forgotten password:** `password-reset`, `password-reset-done`,
  `password_reset_confirm`. The confirmation page looks the same whether the email is
  registered or not. If the link has expired, that same page also offers a resend form
  (posting back to `password-reset`) instead of requiring an admin reset — see
  [`authentication.md`](authentication.md).
- **Login by email link:** `magic-link-request`, `magic-link-sent`,
  `magic-link-confirm-token`, `magic-link-confirm`. See
  [`authentication.md`](authentication.md).
- **`healthz`** and the root `/` redirect.
- **`ical-feed`** (`calendrier/<token>.ics`): the personal calendar feed. Calendar apps
  cannot log in, so the secret token in the URL identifies the account. An invalid
  token returns 404. The feed only contains what that account can see. Staff do not get
  extra events in their feed. Birthdays of people whose privacy choice is "redact" are
  left out.
- **`branding-asset`** (`/branding/logo`, `/branding/favicon`): the logo and icon must
  show on the login page. Only these two files can be reached this way.
- **`javascript-catalog`** (`/jsi18n/`): the translations used by JavaScript. The login
  pages need it too. It contains no personal data. See [`i18n.md`](i18n.md).
- **`set-language`** (`/annuaire/langue/`): the language switch. It works on the login
  page too. For a logged-in user, it also saves the choice in their account.
- **`privacy-notice`** (`confidentialite/`): the privacy page. Visitors must be able to
  read it before they sign up. **Accepting** it (`privacy-notice-accept`) requires login.

Do not add a page to this list without a clear reason. Remember that a new public page
will not work until you mark it with `login_not_required`.

Django's own login and password pages are already public in Django, so our versions
inherit this. Our other public pages are marked explicitly.

**Uploaded files** (`/media/...`: profile photos, place photos, blog attachments) require
login.

**Forced password change:** a user who must change their password is sent to the
password change page on every page. The password reset link and the magic link are
exceptions, so these users can still use them.

**Rate limiting.** Three public forms send emails: `signup`, `password-reset` and
`magic-link-request`. Each email address can use them 3 times per hour and 10 times per
day. Each form also accepts at most 60 requests per hour in total, to stop an attack
that uses many different addresses. The limit is based on the email address, not on
the IP address, because the app cannot trust the IP address it receives from the
reverse proxy. When the limit is reached, the form shows an error (HTTP 429). The
message is the same whether the account exists or not.

## Superuser vs staff

Some checks accept staff **or** superuser. Others (`StaffRequiredMixin`,
`AuthorOrStaffRequiredMixin`) only accept staff. In practice, every superuser is also
staff, so this makes no difference today. But an account that is superuser and not
staff could not use the staff-only pages: account creation, duplicates and merge,
GEDCOM import, comment deletion, and editing other people's posts.
