from django.apps import AppConfig


class LearningConfig(AppConfig):
    name = "learning"

    def ready(self):
        from .background_jobs import background_worker
        background_worker.start()
