# -*- coding: utf-8 -*-
"""
    Podcasts via Podcatcher
    ~~~~~~~~
    Adopted from Sebastian Hutter https://github.com/sebastianhutter/podcaster/
"""

import appconfig
import logging
import os
import schedule
import traceback
import time

from podcatcher import Podcatcher


def main():
    """ Initialise Config Object and Podcaster Class (Database and Podcast YAML File). """
    PODCASTER_ENV = os.getenv('PODCASTER_ENV', "development")
    if PODCASTER_ENV.lower() == "development":
        config = appconfig.DevelopmentConfig
    else:
        config = appconfig.ProductionConfig
    if config.DEBUG:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Check if we need to disable SSL Verification.
    if config.DISABLE_SSL_VERIFY:
        logger.debug('disable ssl verification (https) for program execution')
        import ssl
        if hasattr(ssl, '_create_unverified_context'):
            ssl._create_default_https_context = ssl._create_unverified_context
    logger.debug('initialize podcaster object')
    podcaster = Podcatcher(config.DATABASE, config.PODCASTS_DIR, config.PODCASTS, config.TEMP_DIR)

    # Initialize feeds and download podcasts.
    # If a Schedule Value is set (higher then 0); additional downloads will be started.
    if config.SCHEDULE > 0:
        logger.info('Re-start download every {} minutes'.format(config.SCHEDULE))
        schedule.every(int(config.SCHEDULE)).minutes.do(podcaster.get_podcaster_file)
        schedule.every(int(config.SCHEDULE)).minutes.do(podcaster.parse_feeds)
        schedule.every(int(config.SCHEDULE)).minutes.do(podcaster.download_podcasts)
        while 1:
            schedule.run_pending()
            time.sleep(1)


if __name__ == '__main__':
    # configure logger: http://docs.python-guide.org/en/latest/writing/logging/
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s'))
    logger.addHandler(handler)
    try:
        main()
    except Exception as err:
        logger.error(err)
        traceback.print_exc()
