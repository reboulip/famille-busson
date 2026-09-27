from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.utils.http import base36_to_int


class _TimeoutCeilingTokenGenerator(PasswordResetTokenGenerator):
    """Shared base for a token generator with its own settings-driven timeout,
    on top of the signature check and Django's own PASSWORD_RESET_TIMEOUT
    ceiling (both already enforced by the parent's check_token)."""

    #: settings attribute name holding the timeout in seconds -- set by subclasses.
    timeout_setting_name: str

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
        timeout = getattr(settings, self.timeout_setting_name)
        if (self._num_seconds(self._now()) - ts) > timeout:
            return False
        return True


class MagicLinkTokenGenerator(_TimeoutCeilingTokenGenerator):
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
    timeout_setting_name = "MAGIC_LINK_TIMEOUT"


class SelfServiceResetTokenGenerator(_TimeoutCeilingTokenGenerator):
    """Token generator for a member-requested password reset or an expired
    invitation link's self-service resend (18.1) -- shorter-lived than a
    staff-sent invitation (which still uses Django's own default_token_generator
    at settings.PASSWORD_RESET_TIMEOUT), and salt-isolated from both that and
    the magic-link generator for the same replay-prevention reason as above.
    """

    key_salt = "annuaire.tokens.SelfServiceResetTokenGenerator"
    timeout_setting_name = "SELF_SERVICE_RESET_TIMEOUT"


class AnyOfTokenChecker:
    """Accepts a token if any of the wrapped generators does -- lets a single
    confirm view honour tokens minted by different flows with different
    lifetimes (a staff-sent invitation vs. a self-service reset) without
    weakening either generator's own timeout."""

    def __init__(self, *generators):
        self._generators = generators

    def check_token(self, user, token):
        return any(generator.check_token(user, token) for generator in self._generators)


magic_link_token_generator = MagicLinkTokenGenerator()
self_service_reset_token_generator = SelfServiceResetTokenGenerator()
password_setup_token_checker = AnyOfTokenChecker(default_token_generator, self_service_reset_token_generator)
