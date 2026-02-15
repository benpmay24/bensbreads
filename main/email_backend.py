"""
Email backends for Ben's Breads.

- ResendBackend: Uses Resend HTTP API (port 443) - works on Render and other clouds.
- EmailBackend: Custom SMTP backend with SSL verify option - for local dev with Private Email.
"""
import ssl

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend


class ResendBackend(BaseEmailBackend):
    """
    Send email via Resend HTTP API. Uses HTTPS (port 443) - not blocked by cloud providers.
    Set RESEND_API_KEY in env. From address must use a domain verified in Resend.
    """

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, "RESEND_API_KEY", None)
        if not api_key:
            raise ValueError("RESEND_API_KEY is not configured")

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "onboarding@resend.dev")
        sent = 0

        for message in email_messages:
            payload = {
                "from": message.from_email or from_email,
                "to": list(message.to),
                "subject": message.subject,
            }
            if message.body:
                payload["text"] = message.body
            if message.alternatives:
                for content, mimetype in message.alternatives:
                    if mimetype == "text/html":
                        payload["html"] = content
                        break

            try:
                resp = requests.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10,
                )
                resp.raise_for_status()
                sent += 1
            except requests.RequestException as e:
                if not self.fail_silently:
                    raise
        return sent


class SMTPBackend(SMTPEmailBackend):
    """Custom SMTP backend with optional SSL verification disable. For local dev."""

    def open(self):
        if self.connection:
            return False

        import smtplib

        connection_params = {"timeout": self.timeout or 15}
        if self.use_ssl:
            connection_params["context"] = self._get_ssl_context()

        try:
            self.connection = smtplib.SMTP(
                self.host, self.port, **connection_params
            )
            self.connection.ehlo()
            if self.use_tls and not self.use_ssl:
                self.connection.starttls(context=self._get_ssl_context())
                self.connection.ehlo()
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except Exception:
            if self.fail_silently:
                return False
            raise

    def _get_ssl_context(self):
        ctx = ssl.create_default_context()
        if getattr(settings, "EMAIL_SSL_VERIFY", True) is False:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx
