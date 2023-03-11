""" Data Model and Constants; Adopted from Sebastian Hutter https://github.com/sebastianhutter/podcaster/ """

from sqlobject import SQLObject, DateTimeCol, UnicodeCol, IntCol

YES = [1, "1", "on", "yes", "Yes", "YES", "y", "Y", "true", "True", "TRUE", "t", "T"]

FILE_TYPES = {
    'audio/mpeg': 'mp3',
    'video/x-m4v': 'm4v',
    'audio/x-opus': 'opus',
    'audio/x-ogg': 'ogg',
    'audio/aac': 'aac',
    'audio/mp4': 'm4a',
    'video/mp4': 'm4v',
    'audio/mp3': 'mp3'
}


class SeenEntry(SQLObject):
    """ Table represents a podcast which we have seen / downloaded before. """
    hashed = UnicodeCol()  # hashed title (used for comparison)
    pub_date = DateTimeCol()  # publication date (used for comparison)
    feed_id = UnicodeCol()  # where is the podcast from?
    podcast_title = UnicodeCol()  # unhashed title value of the podcast
    podcast_status = IntCol()  # status of the downloaded podcast - 0 = all fine, 1 = error wile downloading/parsing
