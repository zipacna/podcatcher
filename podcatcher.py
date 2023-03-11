"""
    Podcatcher
    ~~~~~~~~
    Download, transform and shuffle your favourite podcasts.

    Adopted from Sebastian Hutter https://github.com/sebastianhutter/podcaster/
"""

import os
import logging
import time
import requests
import yaml
import hashlib
from urllib.parse import urlparse
from sqlobject import sqlite
import feedparser
from datetime import datetime

from model import SeenEntry, FILE_TYPES
from podcast import Podcast


class Podcatcher(object):
    """ Class to parse Podcast Feeds. """

    def __init__(self, database, podcast_dir, podcast_list, temp_dir):
        """ Initialize the Class -> get the YAML Configuration File. """
        self.database = database
        self.podcast_dir = podcast_dir
        self.podcast_source = podcast_list
        self.podcast_list = None
        self.temp_dir = temp_dir
        self.feeds = []
        self.SeenEntry: SeenEntry
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

        self._init_database()
        self.get_podcaster_file()  # Verify Podcaster Settings File.
        self.parse_feeds()
        self.download_podcasts()

    def get_podcaster_file(self):
        """ Check if the Podcast Settings File is a local File or needs to be downloaded from an URL. """
        parsed_file = urlparse(self.podcast_source)
        if parsed_file.scheme in ['http', 'https']:
            try:
                download_file = os.path.join(self.temp_dir, os.path.basename(parsed_file.path))
                self.logger.debug(f'download podcast settings file {self.podcast_source} to {download_file}')
                response = requests.get(self.podcast_source)
                with open(download_file, 'wb') as f:
                    f.write(response.content)
                self.podcast_list = download_file
            except Exception:
                raise
        else:
            self.podcast_list = self.podcast_source
        if not os.path.exists(self.podcast_list):
            raise Exception(f"podcast settings file '{self.podcast_list}' does not exist")

    def _init_database(self):
        """ Init the SQLite Database with the LastSeen-Table. """
        self.logger.debug("initialize 'seen' database: '" + self.database + "'")
        self.SeenEntry = SeenEntry
        self.SeenEntry._connection = sqlite.builder()(self.database, debug=False)
        self.SeenEntry.createTable(ifNotExists=True)

    def parse_feeds(self):
        """ Load all Feeds from the YAML Config; parse Feed URLs via Feedparser. """
        self.logger.debug(f"load feed configuration: '{self.podcast_list}'")
        with open(self.podcast_list, "r", encoding="utf-8") as stream:
            try:
                feeds = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        # Filter out active Feeds.
        self.feeds = []
        for f in feeds['podcasts']:
            if f['active']:
                self.logger.debug(f"feed '{f['id']}' is Active")
                self.feeds.append(f)
        # Initialize all Feeds with Feedparser.
        for p in self.feeds:
            self.logger.debug(f"Parse feed '{p['id']}' with URL: {p['url']}")
            parsed_feed = feedparser.parse(p['url'])
            # Create an empty List which we will use to store all valid Entries (which we want to download).
            p['entries'] = []
            parsed_feed.entries.reverse()  # Oldest Entries First.
            self.logger.debug(f"Found {len(parsed_feed.entries)} podcasts in feed")
            self.parse_entries(parsed_feed, p)
            self.logger.debug("Total count of valid podcasts for feed is: " + str(len(p['entries'])))

    def parse_entries(self, parsed_feed, p):
        for e in parsed_feed.entries:
            self.logger.debug(f"Parse podcast entry: '{e.title}'")
            # Now that we have the Feed Content, lets get the necessary Info from it.
            # Podcasts older then maxage we will not download; if maxage = 0 -> we always check all Podcasts.
            if p['maxage'] > 0:
                if (datetime.now() - datetime.fromtimestamp(time.mktime(e.published_parsed))).days > p['maxage']:
                    self.logger.debug(f"Podcast '{e.title}' is too old. Will not download it")
                    continue

            # If the Entry is in the Date Range, we need to get some Basic Info from it.
            # We dont need all Meta-Information stored in the Feed, only a few selected Fields.
            # First lets create a Hash from the title, so we can compare it against the entries in our Seen Table.
            # new = we will generate and store the UTF-8 encoded Title as Hash.
            # For older Entries we stored the ASCII encoded Title has has[sic].
            # So we generate both but will store only the UTF-8 Hashes in the Future.
            entry = {'hash': hashlib.sha1(e.title.encode('utf-8', 'ignore')).hexdigest()}
            hash_ascii = hashlib.sha1(e.title.encode('ascii', 'ignore')).hexdigest()

            # Let's check if we worked on this Entry earlier...
            v1entry_exists = self.SeenEntry.select(self.SeenEntry.q.hashed == hash_ascii).count()
            # Let's check if the Entry already exists in the Database. If so we will jump over it.
            v2entry_exists = self.SeenEntry.select(self.SeenEntry.q.hashed == entry['hash']).count() > 0
            if v1entry_exists or v2entry_exists:
                self.logger.debug(f"Podcast '{e.title}' is already in 'Seen' database. Will not download it")
                continue

            # If the Podcast is not already in the Database, gather some Basic Info from its Feed.
            entry.update({'id': e.id, 'published': e.published, 'published_parsed': e.published_parsed,
                          'title': e.title, 'summary': e.summary, 'author': e.author, 'link': e.link})
            # Lets get the first Multimedia Enclosure.
            for enclosure in filter(lambda x: x.get('type') in FILE_TYPES.keys(), e.get('links', [])):
                entry.update({'file_link': enclosure.href, 'file_length': enclosure.length,
                              'file_type': enclosure.type, 'file_ending': FILE_TYPES[enclosure.type]})

            # If no valid Enclosure was found we should not add the Podcast to the List.
            if 'file_link' in entry:
                self.logger.debug(f"Podcast '{e.title}' is valid. Podcast will be downloaded")
                p['entries'].append(Podcast(entry))
            else:
                self.logger.debug(f"Podcast '{e.title}' is invalid. Will not download it")

    def download_podcasts(self):
        self.logger.info(f"loop trough {len(self.feeds)} feeds")
        for feed in self.feeds:
            self.logger.info(f"Run trough feed: {feed['id']}")
            download_dir = os.path.join(self.podcast_dir, feed['id'])
            self.logger.debug(f"Create download directory: {download_dir}")
            os.makedirs(download_dir, exist_ok=True)

            # Loop trough all Podcasts.
            self.logger.info(f"loop trough {len(feed['entries'])} podcast entries")
            for p in feed['entries']:
                try:
                    def override(feedslug, tag, value):
                        if feed[feedslug]:
                            p.overwrite_mp3tag(tag, value)
                    self.logger.info(f"Working on podcast: '{p.title}'")
                    self.logger.info("Downloading podcast file")
                    p.download_file(self.temp_dir)
                    self.logger.info("Load mp3 tags from file")
                    p.load_mp3tags()
                    # If the Feed is set to overwrite the Tags; we will do this now before renaming and moving the File.
                    self.logger.info("Overwrite mp3 tags if necessary")
                    override('overwrite_id3_album', 'album', feed['album'])
                    override('overwrite_id3_artist', 'artist', feed['artist'])
                    override('overwrite_id3_albumartist', 'albumartist', feed['albumartist'])
                    override('overwrite_id3_date', 'date', time.strftime('%Y-%m-%d', p.published_parsed))
                    override('overwrite_id3_title', 'title', p.title)

                    self.logger.info("Move and rename podcast file")
                    p.move_file(self.podcast_dir, feed['id'])
                    self.logger.info("Mark podcast as seen")
                    self.SeenEntry(hashed=p.hash, pub_date=datetime.fromtimestamp(time.mktime(p.published_parsed)),
                                   feed_id=feed['id'], podcast_title=p.title, podcast_status=0)
                except Exception as e:
                    self.logger.error(f"Unable to properly modify podcast: {e}")
                    self.logger.error("Mark download as faulty")
                    self.SeenEntry(hashed=p.hash, pub_date=datetime.fromtimestamp(time.mktime(p.published_parsed)),
                                   feed_id=feed['id'], podcast_title=p.title, podcast_status=1)
