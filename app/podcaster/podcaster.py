# -*- coding: utf-8 -*-
"""
    podcaster
    ~~~~~~~~
    Download, transform and shuffle your favourite podcasts

    Thanks a ton to upodder from where I copied some not so trivial parts!
    https://github.com/m3nu/upodder/
"""

####
# imports
####

import appconfig
import podcast
import logging
import os
import schedule
import traceback
import time

#####
# functions
#####

def main():
    """
        main function.
        initialise config object and Podcaster class
    """

    # load the basic configuration settings (database and podcast yaml file)
    PODCASTER_ENV = os.getenv('PODCASTER_ENV', "development")

    if PODCASTER_ENV.lower() == "development":
        config = appconfig.DevelopmentConfig
    else:
        config = appconfig.ProductionConfig

    if config.DEBUG:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # check if we need to disable ssl verification
    if config.DISABLE_SSL_VERIFY:
        logger.debug('disable ssl verification (https) for program execution')
        import ssl

        if hasattr(ssl, '_create_unverified_context'):
            ssl._create_default_https_context = ssl._create_unverified_context

    # initialize the podcaster object
    logger.debug('initialize podcaster object')
    podcaster = podcast.Podcaster(config.DATABASE, config.PODCASTS_DIR, config.PODCASTS, config.TEMP_DIR)

    # intialize feeds and download podcasts

    # if a schedule value is set (higher then 0)
    # additional downloads will be started
    if config.SCHEDULE > 0:
        logger.info('Re-start download every {} minutes'.format(config.SCHEDULE))
        schedule.every(int(config.SCHEDULE)).minutes.do(podcaster.get_podcaster_file)
        schedule.every(int(config.SCHEDULE)).minutes.do(podcaster.parse_feeds)
        schedule.every(int(config.SCHEDULE)).minutes.do(podcaster.download_podcasts)

        # loop and run scheduled tasks
        while 1:
            schedule.run_pending()
            time.sleep(1)


#####
# main
#####


# configure logger
# http://docs.python-guide.org/en/latest/writing/logging/
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# start app

if __name__ == '__main__':
    try:
        main()
    except Exception as err:
        logger.error(err)
        traceback.print_exc()

