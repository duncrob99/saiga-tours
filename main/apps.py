from django.apps import AppConfig


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        from .models import Article
        from vectordb.shortcuts import autosync_model_to_vectordb

        autosync_model_to_vectordb(Article)

        import main.signals
