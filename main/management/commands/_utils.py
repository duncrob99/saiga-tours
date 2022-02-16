import os
import re
import time
import warnings

import six
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from django.apps import apps
from django.conf import settings
from django.core.validators import EMPTY_VALUES
from django.db import models

warnings.filterwarnings('ignore', category=MarkupResemblesLocatorWarning, module='bs4')


def get_file_fields():
    """
        Get all fields which are inherited from FileField
    """

    # get models

    all_models = apps.get_models()

    # get fields

    fields = []

    for model in all_models:
        for field in model._meta.get_fields():
            if isinstance(field, models.FileField):
                fields.append(field)

    return fields


def get_text_fields():
    """
        Get all fields which are inherited from TextField
    """

    # get models

    all_models = apps.get_models()

    # get fields

    fields = []

    for model in all_models:
        for field in model._meta.get_fields():
            if isinstance(field, models.TextField):
                fields.append(field)

    return fields


def get_used_media():
    """
        Get media which are still used in models
    """

    media = set()

    for field in get_file_fields():
        is_null = {
            '%s__isnull' % field.name: True,
        }
        is_empty = {
            '%s' % field.name: '',
        }

        storage = field.storage

        for value in field.model._base_manager \
                .values_list(field.name, flat=True) \
                .exclude(**is_empty).exclude(**is_null):
            if value not in EMPTY_VALUES:
                media.add(storage.path(value))

    for field in get_text_fields():
        is_null = {
            '%s__isnull' % field.name: True,
        }
        is_empty = {
            '%s' % field.name: '',
        }

        for value in field.model._base_manager \
                .values_list(field.name, flat=True) \
                .exclude(**is_empty).exclude(**is_null):
            soup = BeautifulSoup(value, 'html.parser')
            imgs = soup.find_all("img")
            # texts.add(f'{field.model} - {field.name}')
            for img in imgs:
                # texts.add(f'Matched imgs: {list(map(lambda img: img["src"], imgs))}')
                if 'src' in img.attrs.keys():
                    if img['src'].startswith(settings.MEDIA_URL):
                        media.add(f'{settings.MEDIA_ROOT}/{img["src"].removeprefix(settings.MEDIA_URL)}')

    return media


def get_all_media(exclude=None, minimum_file_age=None):
    """
        Get all media from MEDIA_ROOT
    """

    if not exclude:
        exclude = []

    media = set()
    initial_time = time.time()

    for root, dirs, files in os.walk(six.text_type(settings.MEDIA_ROOT)):
        for name in files:
            path = os.path.abspath(os.path.join(root, name))
            relpath = os.path.relpath(path, settings.MEDIA_ROOT)

            if minimum_file_age:
                file_age = initial_time - os.path.getmtime(path)
                if file_age < minimum_file_age:
                    continue

            for e in exclude:
                if re.match(r'^%s$' % re.escape(e).replace('\\*', '.*'), relpath):
                    break
            else:
                media.add(path)

    return media


def get_unused_media(exclude=None, minimum_file_age=None):
    """
        Get media which are not used in models
    """

    if not exclude:
        exclude = []

    all_media = get_all_media(exclude, minimum_file_age)
    used_media = get_used_media()

    return all_media - used_media


def remove_unused_media():
    """
        Remove unused media
    """
    remove_media(get_unused_media())


def remove_media(files):
    """
        Delete file from media dir
    """
    for filename in files:
        os.remove(os.path.join(settings.MEDIA_ROOT, filename))


def remove_empty_dirs(path=None):
    """
        Recursively delete empty directories; return True if everything was deleted.
    """

    if not path:
        path = settings.MEDIA_ROOT

    if not os.path.isdir(path):
        return False

    listdir = [os.path.join(path, filename) for filename in os.listdir(path)]

    if all(list(map(remove_empty_dirs, listdir))):
        os.rmdir(path)
        return True
    else:
        return False
