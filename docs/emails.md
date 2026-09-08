# Outgoing emails

The messages the app sends, how they are built, and how to look at one without
waiting for it to happen.

The design pass behind them — palettes, the full vs. restrained treatment split, the
per-email specs — is [`design/emails/SPEC.md`](https://github.com/reboulip/famille-busson/blob/main/design/emails/SPEC.md).
That folder is a throwaway review artifact; this page is the reference for what shipped.
The site uses the same palettes — see [`design_system.md`](design_system.md).

## The flows

| Flow | Triggered by | Treatment | Builder |
|---|---|---|---|
| Birthday reminder | background queue, daily 07:00 UTC (`annuaire.tasks.send_daily_birthday_reminders`) | full ridge | `annuaire.emails.birthday_reminder` |
| New blog post | `post_save` on `BlogPost` (`publications/signals.py`) | full ridge | `annuaire.emails.new_blog_post` |
| Event announcement | `post_save` on `Event` (`events/signals.py`) | full ridge | `annuaire.emails.event_announcement` |
| Event reminder | background queue, daily 08:00 UTC (`events.tasks.send_event_reminders`) | full ridge | `annuaire.emails.event_reminder` |
| Account setup / reset | staff bulk-create + resend (`BulkAccountCreateView`) | flat horizon | `annuaire.emails.account_setup` |
| Password reset | `AccountPasswordResetView` | flat horizon | Django, `html_email_template_name` |
| Magic link | `MagicLinkRequestView` | flat horizon | Django, `html_email_template_name` |

**Who receives what did not change** with the HTML rework: the opt-in checkboxes,
deceased-profile exclusion and the connection-cycling bulk sender are all as they were.
This was a rendering swap.

**Event announcement and reminder share one opt-out:** `Settings.notify_on_event`
covers both flows (a single preference, not two) — unlike birthday/new-post, which each
have their own `notify_on_*` flag. `events.tasks.notification_audience(event)` is the
shared audience computation for both: opted in (`notify_on_event=True`), a non-empty
email, not deceased, and — if the event is group-restricted — a member of one of its
groups. The reminder additionally excludes anyone who RSVP'd "non" on that event.

## Where the code lives

| File | What it holds |
|---|---|
| `annuaire/emails.py` | One builder per flow — decides the context, returns an `OutgoingEmail`. |
| `annuaire/email_utils.py` | `OutgoingEmail`, `InlineImage`, `build_message`, `send_bulk_emails`, `send_one_email`. Transport and MIME. |
| `annuaire/templates/annuaire/emails/_base.html` | The shared shell: ridge, wordmark, eaves line, card, footer. |
| `annuaire/templates/annuaire/emails/_horizon.html` | The restrained ridge (credential flows). |
| `annuaire/templates/annuaire/emails/_wordmark.html` | The "Famille Busson" wordmark, linked to `site_base_url` when given, plain text otherwise. Included by both `_base.html` and `_horizon.html`. |
| `annuaire/templates/annuaire/emails/_button.html` | The single call to action. |
| `annuaire/management/commands/preview_emails.py` | Renders or sends any flow on demand. |

Builders are kept out of the views and commands that trigger them so the same code path
feeds both the real sender and the preview command, and so each template's context is
decided in exactly one place.

## Rules that are easy to break

- **Every message ships both halves.** A multipart with no text part is unreadable in a
  text-only client and reads as a spam signal. `render_email()` returns the pair;
  `test_every_flow_ships_a_plain_text_part` guards it.
- **Nothing may rely on an external image.** Most clients block images until the reader
  clicks "download images" — including on first open, which is when these are read. The
  mountain is built from bordered-`<div>` triangles, and Outlook (whose Word engine
  renders that unreliably) gets a flat sky band via an MSO conditional.
- **A member photo cannot be linked.** `MEDIA_URL` is served by `media_serve` behind
  `@login_required` on purpose; an email client is not logged in and would render the
  login page. Photos are embedded — see below.
- **Inline CSS on every element.** The `<style>` block carries only what must be a rule
  rather than an inline style: the `prefers-color-scheme: dark` overrides (inline styles
  otherwise win) and the mobile breakpoint.
- **CTA fill is `#9C4A22` (ember), never `#D9793F` (alpenglow).** Card-tinted text on
  alpenglow measures 2.98:1 and fails AA for the button label; on ember it is 5.90:1.
- **Subjects are frozen.** Members may filter on them. Changing one is a product
  decision, not a styling one.
- **The "Gérer mes préférences" link is recipient-aware, when a recipient is known.**
  `birthday_reminder()`/`new_blog_post()`/`event_announcement()`/`event_reminder()` take
  an optional keyword-only `recipient: Person | None` and, when given, deep-link
  `settings_url` to that person's
  own `/personne/<pk>/update#notifications` instead of the generic `edit-my-profile`
  redirect. Dropping the `recipient` argument silently falls back to the generic link —
  easy to miss at a new call site. Absolute URLs (including this one) are built from
  `SITE_BASE_URL`, which must resolve to the real domain outside a request context — see
  [`deployment.md`](deployment.md#environment-variables).
- **The wordmark and "site de la famille Busson" footer text link home, when a base URL
  is available.** `_wordmark.html` renders an `<a href="{{ url }}">` when `url` is
  passed, or falls back to a plain `<span>` otherwise — needed because the two Django
  stock flows (password reset, magic link) render through `PasswordResetView`'s own
  machinery rather than `annuaire.emails`' builders, so `AccountPasswordResetView`/
  `MagicLinkRequestView` pass `site_base_url` in via `extra_email_context` instead.
  Forgetting that on a new Django-stock email flow silently degrades to plain text, not
  an error.
- **New-post notifications are enqueued from `transaction.on_commit`, not straight off
  `post_save`.** `BlogPost`'s authors are a M2M, attached by the view *after* the row is
  saved — a notification built directly in the `post_save` receiver saw an empty author
  list and rendered "Par " with no names. `publications/tasks.py`'s
  `send_blog_post_notification` re-queries the post (including its authors) from the
  background queue, by which point the transaction that saved both the row and its M2M
  has already committed — so the `on_commit` wrapper is what makes the *enqueue* wait
  for that commit, not what builds the message. One task is enqueued per subscriber
  (by post PK + plain recipient email, never a model instance), so a provider hiccup on
  one recipient retries independently instead of the whole batch's message being lost
  or, before this queue existed, silently dropped for everyone (see
  [`background_tasks.md`](background_tasks.md)).
- **Event announcements are enqueued from `transaction.on_commit` for the same reason,
  with a higher stake.** `Event.groups` is a M2M populated by `form.save_m2m()` *after*
  the row saves, so computing the announcement audience directly in `events/signals.py`'s
  `post_save` receiver would see zero groups and mail a restricted event's date and
  address to the whole family, not just its intended audience. `events.tasks.
  notification_audience(event)` is only ever called from inside `transaction.on_commit`.

## The embedded birthday photo

`annuaire.emails.birthday_photo()` reads the file and returns an `InlineImage`, which
`build_message()` nests as:

```
multipart/alternative
├── text/plain          ← text-only clients stop here and never see a loose attachment
└── multipart/related
    ├── text/html
    └── image/…         ← Content-ID, disposition inline, referenced as src="cid:…"
```

Django 6 cannot build that on its own (`mixed_subtype` was removed and `_add_attachments`
hardcodes `make_mixed()`), so `_InlineImageEmail.message()` lets Django build the
alternative pair and then converts the HTML leaf in place with the stdlib's
`make_related()` / `add_related()`.

It falls back to the initials disc when the person has no photo, the file cannot be read
(a cleaned-up upload, an unmounted media volume) or it exceeds `MAX_INLINE_PHOTO_BYTES`
(400 KB) — the photo travels in **every copy** of the message, one per subscriber.

## Looking at an email

```bash
# render every flow to /tmp/email-preview/ as .html + .txt
uv run python manage.py preview_emails

# just one
uv run python manage.py preview_emails --flow birthday

# send it to a real address, through the configured EMAIL_BACKEND
uv run python manage.py preview_emails --flow magic-link --to moi@example.com
```

It renders against real rows when the database has them and a stub otherwise. The two
`PasswordResetView` flows are previewed with a fake uid/token, so their links will not
authenticate — everything else about them is what a real send produces.
