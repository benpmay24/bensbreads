import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bensbreads.settings')

app = Celery('bensbreads')

# Load configuration from Django settings, all configuration keys should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    'send-daily-update-reminder': {
        'task': 'main.tasks.send_daily_update_reminder',
        'schedule': crontab(minute=0, hour=22),  # Run at 10 PM (22:00) every day
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
