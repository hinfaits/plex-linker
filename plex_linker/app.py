import os
import re
import sys
import errno
import argparse
import logging

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.propagate = False

def create_path(path):
    """
    Make directory structure `path` (including all parents) on the system, or
    do nothing if the path exists
    """
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise exception


def remove_path(path):
    """
    Remove directory structure `path` (including all parents) on the system if
    (sub)directories are empty, do nothing if directories are not empty
    """
    try:
        os.removedirs(path)
    except OSError as exception:
        if exception.errno != errno.ENOTEMPTY:
            raise exception


def put_whitespace(in_str):
    """
    Replace periods (.), underscores (_) and hyphens (-) in `in_str` with spaces
    """
    return in_str.replace(".", " ").replace("-", " ").replace("_", " ")


class TvFormat(object):
    """
    See article 16.4, at line 526:
    https://raw.githubusercontent.com/hinfaits/plex-linker/master/doc/The.720p.TV.x264.Releasing.Standards.2016-TVx264
    """
    @staticmethod
    def get(title):
        """
        Get the corresponding subclass of `TvFormat` for `title`
        """
        formats = (Weekly, Mini, Daily, Single, Other)
        for format in formats:
            if re.search(format.title_format, title, re.IGNORECASE) is not None:
                return format
        # Other should be matched and None should never be returned
        return None

    @classmethod
    def metadata(cls, title):
        """
        Get a dictionary of metadata extracted from `title`
        """
        res = re.search(cls.title_format, title, re.IGNORECASE)
        ret = dict()
        if res is not None:
            for i in range(len(cls.groups)):
                ret[cls.groups[i]] = res.group(i + 1)
            return ret
        else:
            return None

    @classmethod
    def plex_name(cls, title):
        """
        Get the filename Plex expects for `title`
        """
        raise NotImplementedError("Implemented by subclass.")

    @classmethod
    def plex_dir(cls, title):
        """
        Get the directory structure Plex expects for `title`
        """
        raise NotImplementedError("Implemented by subclass.")

    @classmethod
    def dir(cls, title):
        """
        Get an arbitrary "nice" directory structure for `title`
        """
        raise NotImplementedError("Implemented by subclass.")


class Single(TvFormat):
    """
    Covers 16.4.1 of the scene naming standards (720p 2016)
    """
    title_format = "^(.+)\.(\d\d\d\d)\..+$"
    groups = ("name", "year",)

    @classmethod
    def plex_name(cls, title):
        data = cls.metadata(title)
        return "{} - {} - {}".format(
            put_whitespace(data['name']),
            data['year'],
            title
        )

    @classmethod
    def plex_dir(cls, title):
        data = cls.metadata(title)
        return os.path.join(
            put_whitespace(data['name']),
            put_whitespace("{}".format(data['year']))
        )

    @classmethod
    def dir(cls, title):
        data = cls.metadata(title)
        return data['name'].lower()


class Weekly(TvFormat):
    """
    Covers 16.4.2, 16.4.3, 16.4.4 of the scene naming standards (720p 2016)
    """
    title_format = "^(.+)\.S(\d+)E([^\.]+)\..+$"
    groups = ("name", "season", "episode",)

    @classmethod
    def plex_name(cls, title):
        data = cls.metadata(title)
        return "{} - s{}e{} - {}".format(
            put_whitespace(data['name']),
            data['season'],
            data['episode'],
            title
        )

    @classmethod
    def plex_dir(cls, title):
        data = cls.metadata(title)
        return os.path.join(
            put_whitespace(data['name']),
            "Season {}".format(data['season'])
        )

    @classmethod
    def dir(cls, title):
        data = cls.metadata(title)
        return data['name'].lower()


class Mini(TvFormat):
    """
    Covers 16.4.5 of the scene naming standards (720p 2016)
    """
    title_format = "^(.+)\.Part\.([^\.]+)\..+$"
    groups = ("name", "part",)

    @classmethod
    def plex_name(cls, title):
        data = cls.metadata(title)
        return "{} - s01e{} - {}".format(
            put_whitespace(data['name']),
            data['part'],
            title
        )

    @classmethod
    def plex_dir(cls, title):
        data = cls.metadata(title)
        return os.path.join(
            put_whitespace(data['name']),
            "Season 01"
        )

    @classmethod
    def dir(cls, title):
        data = cls.metadata(title)
        return data['name'].lower()


class Daily(TvFormat):
    """
    Covers 16.4.6 of the scene naming standards (720p 2016)
    """
    title_format = "^(.+)\.(\d\d\d\d)\.(\d\d)\.(\d\d)\..+$"
    groups = ("name", "year", "month", "day",)

    @classmethod
    def plex_name(cls, title):
        data = cls.metadata(title)
        return "{} - {} {} {} - {}".format(
            put_whitespace(data['name']),
            data['year'],
            data['month'],
            data['day'],
            title
        )

    @classmethod
    def plex_dir(cls, title):
        data = cls.metadata(title)
        return os.path.join(
            put_whitespace(data['name']),
            "{}".format(data['year'])
        )

    @classmethod
    def dir(cls, title):
        data = cls.metadata(title)
        return data['name'].lower()


class Other(TvFormat):
    """
    Matches any format
    """
    title_format = ".*"
    groups = tuple()

    @classmethod
    def plex_name(cls, title):
        return title

    @classmethod
    def plex_dir(cls, title):
        return "Uncategorized"

    @classmethod
    def dir(cls, title):
        return "Uncategorized".lower()


class Show(object):
    def __init__(self, filename, filepath):
        self.name = filename
        self.path = filepath
        self.format = TvFormat.get(self.name)

    def metadata(self):
        return self.format.metadata(self.name)

    def plex_dir(self):
        return self.format.plex_dir(self.name)

    def plex_name(self):
        return self.format.plex_name(self.name)


class Linker(object):
    def __init__(self, source_dir, target_dir):
        """
        `source_dir` is where Linker() should look for files, `target_dir` is 
        where Linker() should make links
        """
        self.source_dir = source_dir
        self.target_dir = target_dir

    def make_links(self):
        for path, dirs, files in os.walk(self.source_dir):
            # path is the directory we're in
            # dirs are the directories found
            # files are the files found
            for name in files:
                pathname = os.path.join(path, name)
                show = Show(name, path)
                plex_path = os.path.join(self.target_dir, show.plex_dir())
                plex_name = show.plex_name()
                plex_pathname = os.path.join(plex_path, plex_name)
                create_path(plex_path)
                try:
                    # OSError.EEXIST will be raised if the link already exists
                    os.symlink(pathname, plex_pathname)
                    logger.info("Made symlink {} -> {}".format(plex_pathname,
                                                               pathname))
                except OSError as exception:
                    if exception.errno != errno.EEXIST:
                        raise
                    logger.debug("Symlink already exists at {}".format(plex_pathname))

    def delete_broken_links(self):
        for path, dirs, files in os.walk(self.target_dir):
            for name in files:
                pathname = os.path.join(path, name)
                try:
                    # OSError.ENOENT will be raised if the link is broken
                    os.stat(pathname)
                except OSError as exception:
                    if exception.errno != errno.ENOENT:
                        raise
                    else:
                        os.remove(pathname)
                        logger.info("Removed broken symlink {}".format(pathname))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=str, help="Directory containing your TV")
    parser.add_argument("destination", type=str, help="The directory for symlinks to be made in")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(console_handler)
    if args.verbose:
        logger.setLevel(level=logging.DEBUG)
    else:
        logger.setLevel(level=logging.INFO)

    if not os.path.exists(args.source):
        logger.error("Source path [{}] not found.".format(args.source))
        return 1
    if not os.path.exists(args.destination):
        logger.error("Destination path [{}] not found.".format(args.destination))
        return 1

    linker = Linker(args.source, args.destination)
    linker.make_links()
    linker.delete_broken_links()


if __name__=="__main__":
    main()
