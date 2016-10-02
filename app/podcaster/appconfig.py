# -*- coding: utf-8 -*-
"""
    appconfig
    ~~~~~~~~
    application configuration for podcaster
"""

import os
import tempfile

class AppConfig(object):
    """
        Basic Flask App configuration
    """
    DEBUG = False
    # path to sqlite database
    DATABASE = os.getenv('PODCASTER_DB', os.path.join(os.path.expanduser("~"), "podcaster.db"))
    # path to podcasts settings file
    PODCASTS = os.getenv('PODCASTER_SETTINGS', os.path.join(os.path.expanduser("~"), "podcaster.settings"))
    # path to podcasts directory
    PODCASTS_DIR = os.getenv('PODCASTER_DIR', os.path.join(os.path.expanduser("~"), "podcasts"))
    # the temporary directory for downloads
    TEMP_DIR = os.getenv('PODCASTER_TEMP', os.path.join(tempfile.gettempdir(), "podcasts"))
    # need to disable ssl verification to download some of my feeds
    DISABLE_SSL_VERIFY = True

class DevelopmentConfig(AppConfig):
    """
        Load development specific settings
    """
    DEBUG = True

class ProductionConfig(AppConfig):
    """
        Load production specific settings
    """
    DEBUG = False