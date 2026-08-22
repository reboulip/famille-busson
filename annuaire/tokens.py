from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import base36_to_int


class MagicLinkTokenGenerator(PasswordResetTokenGenerator):
    """Token generator for the passwordless "magic link" login flow.

    Uses its own key_salt, distinct from Django's default password-reset
    salt -- without this, a live password-reset URL shown on screen to staff
    (see bulk_account_create.html) could be replayed at the magic-link
    endpoint to silently log in as another member.

    On top of the signature check and Django's own PASSWORD_RESET_TIMEOUT
    ceiling (both enforced by the parent's check_token), also enforce the
    shorter settings.MAGIC_LINK_TIMEOUT.
    """

    key_salt = "annuaire.tokens.MagicLinkTokenGenerator"

    def check_token(self, user, token):
        if not super().check_token(user, token):
            return False
        try:
            ts_b36, _ = token.split("-")
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False
        # ts is expressed in _num_seconds() units (seconds since 2001-1-1, see
        # the parent class), not a raw epoch/self._now() value -- reuse
        # _num_seconds() here too so both sides of the comparison share units.
        if (self._num_seconds(self._now()) - ts) > settings.MAGIC_LINK_TIMEOUT:
            return False
        return True


magic_link_token_generator = MagicLinkTokenGenerator()
