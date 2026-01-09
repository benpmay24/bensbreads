from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Send daily update reminder email'

    def handle(self, *args, **options):
        email = 'benpmay24@gmail.com'
        subject = 'Daily Update Reminder - Share Something Interesting Today!'
        
        message = f"""Hello Ben,

It's time to capture something interesting about today in your Daily Update!

Visit your Daily Update page to add an entry:
{settings.SITE_URL}/daily-update/

Remember: You can only add one entry per day, and you can edit it until midnight.

Best regards,
Ben's Breads
"""
        
        self.stdout.write(f"Attempting to send email...")
        self.stdout.write(f"  From: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"  To: {email}")
        self.stdout.write(f"  Subject: {subject}")
        self.stdout.write(f"  Email Backend: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"  Email Host: {settings.EMAIL_HOST}")
        
        try:
            num_sent = send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Successfully sent {num_sent} email(s) to {email}'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'✗ Failed to send email: {str(e)}'
                )
            )
