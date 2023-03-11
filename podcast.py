# -*- coding: utf-8 -*-
"""
    Podcast
    ~~~~~~~~
    Adopted from Sebastian Hutter https://github.com/sebastianhutter/podcaster/
"""

import logging
import time
import os
import sys
import shutil
import requests
from clint.textui import progress
from slugify import slugify

# TODO: decide on comment style (https://stackoverflow.com/q/56011) and finish refactoring

import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp3 import HeaderNotFoundError

from model import YES


class Podcast(object):
    """ Class to download and transform single podcasts. """
    __slots__ = ['logger', 'file_link', 'hash', 'file_ending', 'temp_file', 'mp3tags', 'published_parsed', 'title',
                 'id', 'published', 'summary', 'author', 'title', 'link', 'file_length', 'file_type']

    def __init__(self, *initial_data, **kwargs):
        """ Init by Dict. """
        self.temp_file = None
        self.mp3tags = None
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])
        self.logger = logging.getLogger('podcast')

    def download_file(self, download_dir):
        """ Download the podcast file to the specified directory. """
        try:
            self.logger.debug("Download podcast file: '" + self.file_link + "'")
            r = requests.get(self.file_link, stream=True, timeout=25)
            with open(os.path.join(download_dir, self.hash + "." + self.file_ending), 'wb') as f:
                if 'content-length' in r.headers:
                    total_length = int(r.headers['content-length'])
                    r_iter = progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length / 1024) + 1)
                else:
                    r_iter = r.iter_content(chunk_size=1024)
                for chunk in r_iter:
                    if chunk:
                        f.write(chunk)
                        f.flush()
        except KeyboardInterrupt:
            try:
                user_wish = input("Do you like to mark item as read? (y/n) or quit? (Ctrl+c): ")
                return user_wish in YES
            except KeyboardInterrupt:
                print("\nQuitting")
                sys.exit()
        # save path to downloaded file
        self.temp_file = os.path.join(download_dir, self.hash + "." + self.file_ending)
        if os.path.getsize(self.temp_file) == 0:
            raise IOError("File was not properly downloaded")
        self.logger.debug("podcast saved as: '" + self.temp_file + "'")

    def load_mp3tags(self):
        """ Function loads mp3 Tags from a downloaded File; First empty then Filled. """
        def tag_exists(tag: str):
            if tag in audio:
                self.mp3tags[tag] = audio[tag][0]
            self.logger.debug(f"read tag {tag}: '{self.mp3tags[tag]}'")
        self.mp3tags = {'album': '', 'title': '', 'tracknumber': '', 'artist': '', 'albumartist': ''}
        try:
            audio = EasyID3(self.temp_file)
        except ID3NoHeaderError:
            self.logger.error("Unable to read mp3 tags from file!")
            return
        tag_exists('album')
        tag_exists('title')
        tag_exists('tracknumber')
        tag_exists('artist')
        tag_exists('albumartist')

    def overwrite_mp3tag(self, tag, value):
        """ Overwrite the specified mp3tag with the specified value. """
        self.logger.debug(f"overwrite tag '{tag}' with value '{value}'")
        try:
            audio = EasyID3(self.temp_file)  # Attempt to get id3 Tags from the File.
        except ID3NoHeaderError:
            audio = mutagen.File(self.temp_file, easy=True)
            audio.add_tags()
        except HeaderNotFoundError:
            raise
        audio[tag] = str(value)
        audio.save()

    def move_file(self, podcast_dir, feed_id):
        """
            This Function renames the downloaded File to a more human readable Format,
            currently the Format is the same for all downloaded Files.

            <Published Year>_<Published Month>_<Published Day>_<feed id>_<track number>_<podcast title>.<file ending>
        """
        timestamp = time.strftime("%Y-%m-%d_%H-%M", self.published_parsed)
        tracknumber = f'{self.mp3tags["tracknumber"]}_' if self.mp3tags['tracknumber'] else ''
        filename = slugify(f'{timestamp}_{feed_id}_{tracknumber}{self.title}') + "." + self.file_ending
        target_path = os.path.join(podcast_dir, feed_id, filename)
        self.logger.debug(f'moving and renaming file from "{self.temp_file}" to "{target_path}"')
        shutil.move(self.temp_file, target_path)
