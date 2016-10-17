#!/usr/bin/python2
import os
import re
import errno
import ConfigParser

from time import sleep

def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text  # or whatever

def create_path(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

def remove_path(path):
    try:
        os.removedirs(path)
    except OSError as exception:
        if exception.errno != errno.ENOTEMPTY:
            raise

class Config():
    def __init__(self):
        self.config = ConfigParser.SafeConfigParser()
        self.config.read("./config.ini")
        self.source_dir = self.config.get("settings", "source_directory")
        self.target_dir = self.config.get("settings", "target_directory")

class Show():
    def __init__(self, filename, path):
        self.file = filename
        self.path = path
        self.generate_metadata()

    def generate_metadata(self):
        res = re.search("^(.+)\.S(\d+)E([E\d-]+)\..+$", self.file)
        if res is not None:
            self.name = res.group(1)
            self.season = res.group(2)
            self.episode = res.group(3)

    def destination(self):
        """
        Returns the full directory structure of where
        the symlink for the show should go
        """
        config = Config()
        return "{}/{}/Season.{}".format(config.target_dir, self.name, self.season)

    def create_link(self):
        if not hasattr(self, 'name'):
            print "Warning, failed for %s/%s" % (self.path, self.file)
            return
        create_path(self.destination())
        try:
            os.symlink("{}/{}".format(self.path, self.file), "{}/{}".format(self.destination(), self.file))
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

def main():
    config = Config()

    # Try to create symlinks
    for root, dirs, files in os.walk(config.source_dir):
        for f in files:
            show = Show(f, root)
            show.create_link()

    # Remove dead links
    for root, dirs, files in os.walk(config.target_dir):
        for f in files:
            try:
                os.stat("{}/{}".format(root, f))
            except OSError as exception:
                if exception.errno != errno.ENOENT:
                    raise
                else:
                    os.remove("{}/{}".format(root, f))

if __name__=="__main__":
    main()
