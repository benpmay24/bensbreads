from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import datetime, time
from zoneinfo import ZoneInfo

@shared_task
def send_daily_update_reminder():
    """
    Send a daily reminder email at 10 PM (22:00) to benpmay24@gmail.com
    This task should be scheduled to run periodically (e.g., every hour or every 30 minutes)
    """
    # Get current time in UTC
    now_utc = timezone.now()
    
    # Convert to Eastern Time (adjust timezone as needed)
    eastern = ZoneInfo("America/New_York")
    now_eastern = now_utc.astimezone(eastern)
    
    # Check if it's between 10 PM and 10:30 PM (give a 30-minute window)
    current_hour = now_eastern.hour
    current_minute = now_eastern.minute
    
    if current_hour == 22 and current_minute < 30:
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
    
    return 'Not the right time to send email'
