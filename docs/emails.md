# Outgoing emails

The emails the site sends, how they are built, and how to preview them.

The original design work is in
[`design/emails/SPEC.md`](https://github.com/reboulip/famille-busson/blob/main/design/emails/SPEC.md).
That folder was only used for review. This page describes what is actually in the
site. The site uses the same colours as the emails (see
[`design_system.md`](design_system.md)).

## The flows

| Email | Sent when | Header style | Built by |
|---|---|---|---|
| Birthday reminder | Every day at 07:00 UTC | full ridge | `annuaire.emails.birthday_reminder` |
| New blog post | A post is published | full ridge | `annuaire.emails.new_blog_post` |
| Event announcement | An event is created | full ridge | `annuaire.emails.event_announcement` |
| Event reminder | Every day at 08:00 UTC, 2 days before an event | full ridge | `annuaire.emails.event_reminder` |
| Account setup | Staff create accounts, or resend the link | flat line | `annuaire.emails.account_setup` |
| Password reset | A user asks for a new password | flat line | Django |
| Magic link | A user asks for a login link | flat line | Django |

Members choose which emails they receive in their profile settings. People marked as
deceased never receive emails.

**Event announcements and event reminders use one setting.** A member who turns off
event emails gets neither. For an event restricted to some groups, only members of
those groups get the emails. People who answered "non" to an event get no reminder.

## Where the code lives

| File | What it holds |
|---|---|
| `annuaire/emails.py` | One function per email. It prepares the content. |
| `annuaire/email_utils.py` | Builds and sends the messages. |
| `annuaire/templates/annuaire/emails/_base.html` | The shared layout: ridge, site name, card, footer. |
| `annuaire/templates/annuaire/emails/_horizon.html` | The simpler header (for password and login emails). |
| `annuaire/templates/annuaire/emails/_wordmark.html` | The site name at the top, with a link to the site. |
| `annuaire/templates/annuaire/emails/_button.html` | The main button. |
| `annuaire/management/commands/preview_emails.py` | Shows or sends any email on demand. |

The same function builds each email for real sending and for the preview command. So
the preview always shows exactly what members receive.

## Rules that are easy to break

- **Every email has an HTML version and a plain-text version.** Without a text version,
  some mail programs cannot show the email, and spam filters are more suspicious. A test
  checks this.
- **No external images.** Most mail programs block images until the reader allows
  them. The mountain drawing is made with HTML and CSS only. Outlook gets a simpler
  version.
- **Member photos cannot be links.** Uploaded files are only visible to logged-in
  users, and a mail program is not logged in. Photos are included inside the email
  instead (see below).
- **Put CSS inline, on each element.** The `<style>` block only holds the dark mode
  and mobile rules, which cannot be inline.
- **The button colour is `#9C4A22` (ember), never `#D9793F` (alpenglow).** Text on
  alpenglow is too hard to read.
- **Do not change email subjects.** Members may use them in mail filters. Changing a
  subject is a product decision.
- **The "Gérer mes préférences" link goes to the recipient's own settings,** if the
  email function receives the `recipient`. If you forget it, the link goes to a generic
  page. All links are built from `SITE_BASE_URL`, which must be the real domain in
  production (see [`deployment.md`](deployment.md#environment-variables)).
- **The site name and the link to the site come from the site settings** (see
  [`site_config.md`](site_config.md)). The password reset and magic link emails are
  built by Django, so they receive these values in a different way
  (`extra_email_context`). If you add another email built by Django, pass
  `site_base_url`, `site_name` and `wordmark` to it too.
- **Each email uses the recipient's language** (French or English), from their account
  settings. If there is no preference, it uses French. See [`i18n.md`](i18n.md).
- **Notifications are sent only after the change is fully saved.** A blog post's
  authors and an event's groups are saved just after the post or event itself. If the
  email were built too early, a post would have no author ("Par " with no name), and a
  restricted event would be emailed to everyone. There is one task per recipient, so if
  one email fails, only that one is tried again (see
  [`background_tasks.md`](background_tasks.md)).

## The embedded birthday photo

The birthday reminder shows the person's photo. The photo is included in the email
itself, and the HTML refers to it. The message is built like this:

```
multipart/alternative
├── text/plain          ← text-only mail programs stop here, and see no attachment
└── multipart/related
    ├── text/html
    └── image/…         ← the photo, shown inside the HTML
```

Django cannot build this structure alone, so `email_utils.py` adjusts the message after
Django builds it.

If the person has no photo, if the file cannot be read, or if it is larger than 400 KB,
the email shows the person's initials instead. The size limit matters because the photo
is sent in every copy of the email, one per subscriber.

## Looking at an email

```bash
# save every email to /tmp/email-preview/ as .html and .txt files
uv run python manage.py preview_emails

# just one
uv run python manage.py preview_emails --flow birthday

# send it to a real address
uv run python manage.py preview_emails --flow magic-link --to moi@example.com
```

The command uses real data from the database if there is any, and example data
otherwise. In the password reset and magic link previews, the links do not work. The
rest is the same as a real email.
