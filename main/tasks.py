from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_daily_update_reminder():
    """
    Send a daily reminder email to benpmay24@gmail.com.
    Scheduled by Celery Beat at 10 PM Eastern.
    """
    email = 'benpmay24@gmail.com'
    subject = 'Daily Update Reminder - Share Something Interesting Today!'
    link = f"{settings.SITE_URL}/daily-update/"

    message = f"""
Hello Ben,

It's 10 PM! Time to capture something interesting about today in your Daily Update.

Visit your Daily Update page to add an entry:
{link}

Remember: You can only add one entry per day, and you can edit it until midnight.

Best regards,
Ben's Breads
"""

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return f'Successfully sent daily update reminder to {email}'
    except Exception as e:
        return f'Failed to send email: {str(e)}'
