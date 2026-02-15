"""
Custom SMTP backend that can disable SSL certificate verification.
Use when your mail provider has cert chain issues (e.g. Private Email).
Set EMAIL_SSL_VERIFY=false in .env to enable.
"""
import ssl

from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend


class EmailBackend(SMTPEmailBackend):
    def open(self):
        if self.connection:
            return False

        import smtplib

        connection_params = {}
        if self.use_ssl:
            connection_params["context"] = self._get_ssl_context()
        else:
            connection_params["timeout"] = self.timeout

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
        from django.conf import settings

        ctx = ssl.create_default_context()
        if getattr(settings, "EMAIL_SSL_VERIFY", True) is False:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx
