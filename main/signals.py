from django.db.models.signals import post_save, post_delete

from vectordb.sync_signals import (
    sync_vectordb_on_delete,
    sync_vectordb_on_create_update
)

from .models import Article, Page, Tour, DestinationDetails

def connect_signals(model):
    post_save.connect(
        sync_vectordb_on_create_update,
        sender=model,
        dispatch_uid='sync_vectordb_on_create_update'
    )

    post_delete.connect(
        sync_vectordb_on_delete,
        sender=model,
        dispatch_uid='sync_vectordb_on_delete'
    )


connect_signals(Article)
connect_signals(Page)
connect_signals(Tour)
connect_signals(DestinationDetails)
