from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, post_delete

from vectordb.sync_signals import (
    sync_vectordb_on_delete,
    #sync_vectordb_on_create_update
)
from vectordb import vectordb

from .models import Article, Page, Tour, DestinationDetails
from job_queue.utils import add_task

def queue_sync(sender, instance, created=None, **kwargs):
    kwargs["signal"] = None  # Avoid having to serialize and deserialize the signal reference
    add_task(sync_vectordb_on_create_update, sender.__name__, instance.pk, created, **kwargs)

def logged_sync(sender, instance, created=None, **kwargs):
    print("syncing on save with paramaters: ", sender, instance, created, kwargs)
    sync_vectordb_on_create_update(sender, instance, created, **kwargs)

def sync_vectordb_on_create_update(model_name, instance_pk, created=None, **kwargs):
    """
    Signal to save or update the vectordb when an instance is created or updated.
    Copied from vectordb.sync_signals.sync_vectordb_on_create_update
    """
    sender = globals()[model_name]
    instance = sender.objects.get(pk=instance_pk)
    content_type = ContentType.objects.get_for_model(instance)
    if (
        not vectordb.filter(
            content_type=content_type, object_id=instance.pk
        ).exists()
    ):
        # Create a new entry in the Vector model
        vector = vectordb.add_instance(instance)
    else:
        # Save the instance to the Vector database if it doesn't exist, else update it
        vector = vectordb.get(content_type=content_type, object_id=instance.pk)

        # Extract the text using the get_vectordb_text method
        text = instance.get_vectordb_text()
        metadata = instance.get_vectordb_metadata()
        vector.metadata = metadata

        if text == vector.text:
            # If the text is the same, don't update the vector
            vector.save()  # save the metadata anyway
            return
        else:
            # Else, update the vector
            vector.text = text

            # Convert the text to embeddings using the Manager's embedding_fn
            vector.embedding = (
                vectordb.embedding_fn(text).astype("float32").tobytes()
            )
            vector.save()

def connect_signals(model):
    post_save.connect(
        queue_sync,
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
