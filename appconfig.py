# -*- coding: utf-8 -*-

import os
import tempfile


class AppConfig(object):
    """ Basic App Configuration; Adopted from Sebastian Hutter https://github.com/sebastianhutter/podcaster/ """
    DEBUG = False

    # Basepath for Podcast Storage
    # USER_DIR = os.path.expanduser("~")
    USER_DIR = ''

    # Path to SQLite Database.
    DATABASE = os.getenv('PODCASTER_DB', os.path.join(USER_DIR, "podcatcher.db"))

    # Path to Podcasts Settings File.
    PODCASTS = os.getenv('PODCASTER_YAML', os.path.join(USER_DIR, "podcatcher.yaml"))

    # Path to Podcasts Directory.
    PODCASTS_DIR = os.getenv('PODCASTER_DIR', os.path.join(USER_DIR, "podcasts"))

    # The temporary Directory for Downloads.
    TEMP_DIR = os.getenv('PODCASTER_TEMP', os.path.join(tempfile.gettempdir(), "podcasts"))

    # Need to disable SSL Verification to download some feeds.
    DISABLE_SSL_VERIFY = True

    # Schedule for Downloading (Minutes).
    SCHEDULE = os.getenv('PODCASTER_SCHEDULE', "0")
    SCHEDULE = int(SCHEDULE)


class DevelopmentConfig(AppConfig):
    """ Load development specific settings """
    DEBUG = True


class ProductionConfig(AppConfig):
    """ Load production specific settings """
    DEBUG = False
