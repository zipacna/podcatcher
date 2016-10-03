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

# environment specific app config
import appconfig

import logging
import time
import yaml
import os
import sys
import shutil
import hashlib
import requests
from clint.textui import progress
from slugify import slugify

import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp3 import HeaderNotFoundError

from sqlobject import SQLObject, sqlite, DateTimeCol, UnicodeCol, IntCol
import feedparser
from datetime import datetime

####
# Constants
####
YES = [1,"1","on","yes","Yes","YES","y","Y","true","True","TRUE","t","T"]

FILE_TYPES = {
    'audio/mpeg': 'mp3', 
    'video/x-m4v': 'm4v', 
    'audio/x-opus': 'opus', 
    'audio/x-ogg': 'ogg',
    'audio/aac': 'aac',
    'audio/mp4': 'm4a',
    'audio/mp3': 'mp3'
}

####
# classes
####

class SeenEntry(SQLObject):
    """
        Table represents a podcast which we have seen / downloaded before
    """
    hashed = UnicodeCol() # hashed title (used for comparison)
    pub_date = DateTimeCol() # publishment date (used for comparison)
    feed_id = UnicodeCol() # where is the podcast from?
    podcast_title = UnicodeCol() # whats the unhashed title value of the podcast
    podcast_status = IntCol() # what is the status of the downloaded podcast - 0 = all fine, 1 = error wile downloading/parsing

class Podcast(object):
    """
        class to download and transform single podcasts 
    """

    def __init__(self, *initial_data, **kwargs):
        """
            initialise the podcast object from dict
            http://stackoverflow.com/questions/2466191/set-attributes-from-dictionary-in-python
        """ 
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

        # load logger into class
        self.logger = logging.getLogger('podcaster')

    def download_file(self, download_dir):
        """
            download the podcast file to the specified directory
        """
        try:
            self.logger.debug("Download podcast file: '" + self.file_link + "'" )
            r = requests.get(self.file_link, stream=True, timeout=25)
            with open(os.path.join(download_dir,self.hash+"."+self.file_ending), 'wb') as f:
                if 'content-length' in r.headers:
                    total_length = int(r.headers['content-length'])
                    r_iter = progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1)
                else:
                    r_iter = r.iter_content(chunk_size=1024)
                for chunk in r_iter: 
                    if chunk:
                        f.write(chunk)
                        f.flush()

        except KeyboardInterrupt:
            try:
                user_wish = input("Do you like to mark item as read? (y/n) or quit? (Ctrl+c): ")
                if user_wish in YES:
                    return True
                else:
                    return False
            except KeyboardInterrupt:
                print("\nQuitting") 
                sys.exit()

        # save path to downloaded file
        self.temp_file = os.path.join(download_dir,self.hash+"."+self.file_ending)
        if os.path.getsize(self.temp_file) == 0:
            raise IOError("File was not properly downloaded")

        self.logger.debug("podcast saved as: '" + self.temp_file + "'")

    def load_mp3tags(self):
        """ 
            function loads mp3 tags from a downloaded file
        """

        # define empty values
        # will be filled up by mp3tags if defined
        self.mp3tags = {}
        self.mp3tags['album'] = ''
        self.mp3tags['title'] = ''
        self.mp3tags['tracknumber'] = ''
        self.mp3tags['artist'] = ''
        self.mp3tags['albumartist'] = ''

        try:
            audio = EasyID3(self.temp_file)
        except ID3NoHeaderError:
            self.logger.error("Not able to read mp3 tags from file")
            return
        
        # if album exists
        if 'album' in audio:
            self.mp3tags['album'] = audio['album'][0]
        self.logger.debug("read tag 'album': '" + self.mp3tags['album'] + "'")

        # if title exists
        if 'title' in audio:
            self.mp3tags['title'] = audio['title'][0]
        self.logger.debug("read tag 'title': '" + self.mp3tags['title'] + "'")

        # if track number exists
        if 'tracknumber' in audio:
            self.mp3tags['tracknumber'] = audio['tracknumber'][0]
        self.logger.debug("read tag 'tracknumber': '" + self.mp3tags['tracknumber'] + "'")

        # if artist exists
        if 'artist' in audio:
            self.mp3tags['artist'] = audio['artist'][0]
        self.logger.debug("read tag 'artist': '" + self.mp3tags['artist'] + "'")

        # if album artist exists
        if 'albumartist' in audio:
            self.mp3tags['albumartist'] = audio['albumartist'][0]
        self.logger.debug("read tag 'albumartist': '" + self.mp3tags['albumartist'] + "'")


    def overwrite_mp3tag(self, tag, value):
        """
            overwrite the specified mp3tag with the specified value
        """
        self.logger.debug("overwrite tag '" + tag + "' with value '" + value + "'")

        # first lets see if we can get id3 tags from the file
        try:
            audio = EasyID3(self.temp_file)
        except ID3NoHeaderError:
            audio = mutagen.File(self.temp_file, easy=True)
            audio.add_tags()
        except HeaderNotFoundError:
            raise

        audio[tag] = unicode(value)
        audio.save() 

    def move_file(self, podcast_dir, feed_id):
        """
            this function renames the downloaded file to a more human readable format.
            currently the format is the same for all downloaded files

            <Published Year>_<Published Month>_<Published Day>_<feed id>_<track number>_<podcast title>.<file ending>
        """
        if self.mp3tags['tracknumber']:
            filename = time.strftime('%Y_%m_%d', self.published_parsed) + "_" + feed_id + "_" + self.mp3tags['tracknumber'] + "_" + self.title
        else:    
            filename = time.strftime('%Y_%m_%d', self.published_parsed) + "_" + feed_id + "_" + self.title 

        filename = slugify(unicode(filename)) + "." + self.file_ending

        self.logger.debug("move and rename file '" + self.temp_file + "' to '" + os.path.join(podcast_dir, feed_id, filename) + "'")
        shutil.move(self.temp_file, os.path.join(podcast_dir, feed_id, filename))
        




class Podcaster(object):
    """
        class to parse feeds.
    """

    def __init__(self, database, podcast_dir, podcast_list, temp_dir):
        """
            initialize the class
            -> get the yaml configuration file
        """
        self.database = database
        self.podcast_dir = podcast_dir
        self.podcast_list = podcast_list
        self.temp_dir = temp_dir

        self.feeds = []
        self.SeenEntry = False

        # load logger into class
        self.logger = logging.getLogger('podcaster')

        # first make sure the podcast temporary and download directory exists
        try:
            self.logger.debug("create podcast directory: '" + self.podcast_dir + "'")
            os.makedirs(self.podcast_dir)
        except OSError:
            if not os.path.isdir(self.podcast_dir):
                raise

        try:
            self.logger.debug("create temp directory: '" + self.temp_dir + "'")
            os.makedirs(self.temp_dir)
        except OSError:
            if not os.path.isdir(self.temp_dir):
                raise

        # initalize the database
        self._init_database()
        # initialize the feeds
        self._init_feeds()
        

    def _init_database(self):
        """
            init the sqlite database with the last seen table
        """
        self.logger.debug("initialize 'seen' database: '" + self.database + "'")
        self.SeenEntry = SeenEntry
        self.SeenEntry._connection = sqlite.builder()(self.database, debug=False)
        self.SeenEntry.createTable(ifNotExists=True)

    def _init_feeds(self):
        """
            load all feeds from the yaml config
            parse feed urls via feedparser
        """

        # load the feed config form the yaml file
        self.logger.debug("load feed configuration: '" + self.podcast_list + "'")
        with open(self.podcast_list, "r") as stream:
            try:
             feeds = yaml.load(stream)
            except yaml.YAMLError as exc:
                print (exc)
        # filter out active feeds
        self.feeds = []

        for f in feeds['podcasts']:
            if f['active']:
                self.logger.debug("feed '" + f['id'] + "' is Active")
                self.feeds.append(f)

        # initialize all feeds with feedparser
        for p in self.feeds:
            # get the feed
            self.logger.debug("Parse feed '" + p['id'] + "' with URL: " + p['url'] + "'")
            parsed_feed = feedparser.parse(p['url'])
            # create an empty list which we will use to store all valid entries (which we want to download)
            p['entries'] = []
            # and reverse its order (oldest entries first)
            parsed_feed.entries.reverse()

            self.logger.debug("Found " + str(len(parsed_feed.entries)) + " podcasts in feed")
            # now loop trough the gathered entries
            for e in parsed_feed.entries:
                self.logger.debug("Parse podcast entry: '" + e.title + "'")
                # now that we have the feed content lets get the necessary info from it
                # podcasts we will not download (everything older then maxage)
                # if maxage = 0 -> we always check all podcasts
                if p['maxage'] > 0:
                    if (datetime.now() - datetime.fromtimestamp(time.mktime(e.published_parsed))).days > p['maxage']:
                        # entry is to old. we cant use it. lets jump to the next one
                        self.logger.debug("Podcast '" + e.title + "' is to old. Will not download it")
                        continue


                # if the entry is in the date range we need to get some basic info from it (we dont need all meta information
                # stored in the feed, only a few selected fields)
                entry = {}

                # first lets create a hash from the title so we can compare it against the entries in our seen sqlite database
                entry['hash'] = hashlib.sha1(e.title.encode('ascii', 'ignore')).hexdigest()

                # lets check if the entry already exists in the database. if so we wil jump over it.
                # Let's check if we worked on this entry earlier...
                if self.SeenEntry.select(self.SeenEntry.q.hashed == entry['hash']).count() > 0:
                    self.logger.debug("Podcast '" + e.title + "' is already in 'seen' database. Will not download it")
                    continue

                # if the podcast is not already in the database gather some basic
                # info from its feed
                entry['id'] = e.id
                entry['published'] = e.published
                entry['published_parsed'] = e.published_parsed
                entry['title'] = e.title
                entry['summary'] = e.summary
                entry['author'] = e.author
                entry['link'] = e.link
                # lets get the first multimedia enclosure
                for enclosure in filter(lambda x: x.get('type') in FILE_TYPES.keys() ,e.get('links',[])):
                    entry['file_link'] = enclosure.href
                    entry['file_length'] = enclosure.length
                    entry['file_type'] = enclosure.type
                    entry['file_ending'] = FILE_TYPES[enclosure.type]

                # if no valid enclosure was found we should not add the podcast to 
                # the list.
                if 'file_link' in entry:
                    self.logger.debug("Podcast '" + e.title + "' is valid. Podcast will be downloaded")
                    p['entries'].append(Podcast(entry))
                else:
                    self.logger.debug("Podcast '" + e.title + "' is invalid. Will not download it")

        self.logger.debug("Total count of valid podcasts for feed is: " + str(len(p['entries'])))

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
    elif PODCASTER_ENV.lower() == "production":
        config = appconfig.ProductionConfig
    else:
        config = appconfig.DevelopmentConfig

    # initialise logging
    logger = logging.getLogger('podcaster')
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
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
    podcaster = Podcaster(config.DATABASE, config.PODCASTS_DIR, config.PODCASTS, config.TEMP_DIR)

    # now loop trough the feeds
    logger.info("loop trough " + str(len(podcaster.feeds)) + " feeds")
    for feed in podcaster.feeds:
        logger.info("Run trough feed: " + feed["id"])

        # create directory for processed podcasts
        try:
            logger.debug("Create download directory " + os.path.join(podcaster.podcast_dir,feed['id']))
            os.makedirs(os.path.join(podcaster.podcast_dir,feed['id']))
        except OSError:
            if not os.path.isdir(os.path.join(podcaster.podcast_dir,feed['id'])):
                raise

        # loop trough all podcasts
        logger.info("loop trough " + str(len(feed['entries'])) + " podcast entries")
        for p in feed['entries']:
            try:
                logger.info("Working on podcast: '" + p.title + "'")
                # download the podcast
                logger.info("Downloading podcast file")
                p.download_file(config.TEMP_DIR)
                # load the mp3tags of the downloaded file
                logger.info("Load mp3 tags from file")
                p.load_mp3tags()
                # if the feed is set to overwrite the tags
                # we will do this now before renaming and moving the file
                logger.info("Overwrite mp3 tags if necessary")
                if feed['overwrite_id3_album']:
                    p.overwrite_mp3tag('album', feed['album']) 
                if feed['overwrite_id3_artist']:
                    p.overwrite_mp3tag('artist', feed['artist']) 
                if feed['overwrite_id3_albumartist']:
                    p.overwrite_mp3tag('albumartist', feed['albumartist']) 
                if feed['overwrite_id3_date']:
                    p.overwrite_mp3tag('date', time.strftime('%Y-%m-%d', p.published_parsed)) 
                if feed['overwrite_id3_title']:
                    p.overwrite_mp3tag('title', p.title) 

                # now rename and move the file
                logger.info("Move and rename podcast file")
                p.move_file(podcaster.podcast_dir, feed['id'])
                # add an entry to our database to mark it as read
                logger.info("Mark podcast as seen")
                podcaster.SeenEntry(hashed=p.hash, pub_date=datetime.fromtimestamp(time.mktime(p.published_parsed)), feed_id=feed['id'], podcast_title=p.title, podcast_status=0)
            except Exception, e:
                logger.error("Unable to properly modify podcast: " + str(e))
                logger.error("Mark download as faulty")
                podcaster.SeenEntry(hashed=p.hash, pub_date=datetime.fromtimestamp(time.mktime(p.published_parsed)), feed_id=feed['id'], podcast_title=p.title, podcast_status=1)

#####
# main
#####

if __name__ == '__main__':
    main()


