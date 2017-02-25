#!/usr/bin/env python

"""
    schedule podcast download
"""

import podcaster
import schedule
import logging
import traceback

# configure logger
# http://docs.python-guide.org/en/latest/writing/logging/
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def main():
    # start scheduler
    schedule.every(int(60)).minutes.do(podcaster.main())

    # loop and run scheduled tasks
    while 1:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    try:
        main()
    except Exception as err:
        logger.error(err)
        traceback.print_exc()
