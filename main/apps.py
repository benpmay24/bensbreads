from django.apps import AppConfig


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        import threading

        def _startup():
            from main.dog_watch.sync_state import recover_on_startup
            recover_on_startup(auto_resume=True)
            from main.dog_watch.scheduler import start_scheduler
            start_scheduler()

        threading.Thread(target=_startup, daemon=True, name='dog-watch-startup').start()
