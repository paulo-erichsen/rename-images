#!/usr/bin/env python3

"""
this script renames images according to the time they were taken
"""
import argparse
import datetime
import json
import logging
import os
import pathlib
import re
import sys

import piexif  # parses exif metadata
import pyheif  # parses heif images
import pymediainfo  # parses videos
from PIL import Image, UnidentifiedImageError  # requires pillow package - parses images

CACHE_FILENAME = "rename_images.json"
TAG_DATETIME_ORIGINAL = 36867  # exif:DateTimeOriginal
TAG_DATETIME_DIGITIZED = 36868  # exif:DateTimeDigitized
TAG_SUBSECTIME_ORIGINAL = 37521  # exif:SubSecTimeOriginal
DEFAULT_PATTERN_NAME_TO_REPLACE = (
    r"^(IMG_\d{4}|(PXL_)?\d{8}_\d{6}(\d{3})?|ABP_\d{4}|DSC\d{5}|\d{3}_\d{4})(\(\d\))?"
)
DEFAULT_DATE_FORMAT = "%Y%m%d_%H%M%S%f"
LEGAL_DATE_FORMAT_CHARS = re.compile(
    r"((%[a-z])*[\w\- ]*)*([\w\- ]*(%[a-z])*)*", flags=re.ASCII | re.IGNORECASE
)

logger = logging.getLogger(__name__)


def date_to_string(date, date_format):
    """converts a date to string. sample output: 20210620_141545333"""
    result = date.strftime(date_format)
    if date_format == DEFAULT_DATE_FORMAT:
        result = result[:-3]
    return result


def parse_jpeg_date(date_str):
    """converts string to date"""
    try:
        return datetime.datetime.fromisoformat(date_str.replace(":", "-", 2))
    except ValueError as e:
        logger.debug(e)
    return None


def parse_mov_date(date_str):
    """converts string to date"""
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
    except (TypeError, ValueError):
        pass
    return None


def get_original_date_jpeg(filepath):
    """
    returns the DateTimeOriginal/DateTimeDigitized exif data from the given jpeg file
    """
    try:
        with Image.open(filepath) as image:
            # NOTE: using old "private" method because new public method
            #       doesn't include this tag. It does include 306 "DateTime"
            #       though, but "DateTime" might differ from "DateTimeOriginal"
            # pylint: disable-next=protected-access
            date_created = image._getexif().get(TAG_DATETIME_ORIGINAL)
            if not date_created:
                date_created = image._getexif().get(TAG_DATETIME_DIGITIZED)
            if date_created:
                # pylint: disable-next=protected-access
                date_created += "." + image._getexif().get(
                    TAG_SUBSECTIME_ORIGINAL, ""
                ).zfill(3)
    except (UnidentifiedImageError, AttributeError):
        logger.debug("unable to parse '%s'", filepath)
        return None

    if date_created:
        date_created = parse_jpeg_date(date_created)

    return date_created


def get_original_date_heif(filepath):
    """returns the DateTimeOriginal exif data from the given heif file"""
    date_created = None

    try:
        image = pyheif.read_heif(filepath)
    except pyheif.error.HeifError:
        logger.debug("unable to parse '%s'", filepath)
        return None

    for data in image.metadata or []:
        if data["type"] == "Exif":
            exif = piexif.load(data["data"])
            date_created = (
                exif.get("Exif", {}).get(TAG_DATETIME_ORIGINAL, b"").decode("utf-8")
            )
            if date_created:
                date_created += "." + exif.get("Exif", {}).get(
                    TAG_SUBSECTIME_ORIGINAL, b""
                ).decode("utf-8").zfill(3)
            break

    if date_created:
        date_created = parse_jpeg_date(date_created)

    return date_created


def get_original_date_mov(filepath):
    """returns the creation time data from the given mov file"""
    general_track = pymediainfo.MediaInfo.parse(filepath).general_tracks[0]
    date_created = parse_mov_date(general_track.comapplequicktimecreationdate)
    return date_created


def process_path(filepath, recursive, pattern, date_format, dry_run, cache):
    """process the given image file or directory containing images"""
    if filepath.is_dir():
        process_directory(filepath, recursive, pattern, date_format, dry_run, cache)
    else:
        process_file(filepath, pattern, date_format, dry_run, cache)


def process_directory(filepath, recursive, pattern, date_format, dry_run, cache):
    """iterates over entries in the directory renaming files if needed"""
    for child in filepath.iterdir():
        if child.is_file():
            process_file(child, pattern, date_format, dry_run, cache)
        elif recursive and child.is_dir():
            process_directory(child, recursive, pattern, date_format, dry_run, cache)


def process_file(filepath, pattern, date_format, dry_run, cache):
    """parses the date created from the file and renames it if needed"""
    logger.debug("processing file: %s", filepath)
    suffix = filepath.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        date_created = get_original_date_jpeg(filepath)
    elif suffix == ".heic":
        date_created = get_original_date_heif(filepath)
    elif suffix == ".mov":
        date_created = get_original_date_mov(filepath)
    else:
        return

    if not date_created:
        logger.warning("unable to find date of creation for: %s", filepath)
        return

    new_path = generate_new_filename(filepath, pattern, date_created, date_format)
    if filepath != new_path and not new_path.is_file():
        logger.info("renaming %s to %s", filepath, new_path)
        if not dry_run:
            # cache: { directory: { new_path: old_path } }
            if str(filepath.parent) not in cache:
                cache[str(filepath.parent)] = {}
            cache[str(filepath.parent)][str(new_path)] = str(filepath)
            try:
                filepath.rename(new_path)
            except PermissionError as e:
                logger.error(e)


def generate_new_filename(filepath, pattern, date_created, date_format):
    """
    returns a new path according to what the new filename should be
    this functions tries to keep file descriptions in place
    example:
    - IMG_9398_picture_at_beach.JPG could become 20210820_123055000_picture_at_beach.JPG
    """
    date_time = date_to_string(date_created, date_format)
    new_name = re.sub(pattern, date_time, filepath.name, count=1)
    if date_time not in new_name:
        new_name = f"{date_time}_{new_name}"
    new_path = pathlib.Path(filepath.parent, new_name)
    if filepath != new_path:
        if new_path.is_file():
            for i in range(10):
                new_name = re.sub(
                    pattern,
                    f"{date_time}_00{i}",
                    filepath.name,
                    count=1,
                )
                if date_time not in new_name:
                    new_name = f"{date_time}_00{i}_{new_name}"
                new_path = pathlib.Path(new_path.parent, new_name)
                if filepath == new_path or not new_path.is_file():
                    break
    return new_path


def revert_path(filepath, recursive, dry_run, cache):
    """reverts changes for a directory or file"""
    if filepath.is_dir():
        revert_directory(filepath, recursive, dry_run, cache)
    else:
        revert_file(filepath, dry_run, cache)


def revert_directory(filepath, recursive, dry_run, cache):
    """iterates over the directory, reverting renames that were made to it"""
    for child in filepath.iterdir():
        if child.is_file():
            revert_file(child, dry_run, cache.get(str(child.parent), {}))
        elif recursive and child.is_dir():
            revert_directory(child, recursive, dry_run, cache)
    if str(filepath) in cache and not cache.get(str(filepath)):
        del cache[str(filepath)]


def revert_file(filepath, dry_run, cache):
    """reverts the rename of the file if it was found in the cache"""
    old_path = cache.get(str(filepath))
    if old_path:
        old_path = pathlib.Path(old_path)
        if not old_path.is_file():
            logger.info("renaming %s to %s", filepath, old_path)
            if not dry_run:
                filepath.rename(old_path)
                del cache[str(filepath)]


def main():
    """
    reads files from the given directory and renames them according to the
    DateTimeOriginal exif metadata
    """
    # argparse settings
    parser = argparse.ArgumentParser(
        description="utility to rename visual media such as images and videos according to their date of creation",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="process files, but don't rename them",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="recursively searches the given directory",
    )
    parser.add_argument(
        "-p",
        "--pattern",
        default=DEFAULT_PATTERN_NAME_TO_REPLACE,
        type=lambda s: re.compile(s, flags=re.IGNORECASE),
        help=r"""pattern of filename to replace. replaces the portion of the filename that matches the given pattern. see re.compile()
    example:
        $ rename_images.py --pattern 'IMG_\d{4}'
            - renames IMG_1999.jpg to 20200222_123045000.jpg -> the pattern matches 'IMG_1999', hence that portion of the filename is replaced by the date
            - renames IMG_1999_example.jpg to 20200222_123045000_example.jpg -> the portion of the string that doesn't match stays intact
            - renames PXL_12345678_example.jpg to 20200222_123045000_PXL_12345678_example.jpg -> no match therefore we just prepend the date
""",
    )
    parser.add_argument(
        "-f",
        "--date-format",
        default=DEFAULT_DATE_FORMAT,
        type=str,
        help="""format of date to use when renaming. renames the file using the given date format. see datetime.strftime()
    example:
        $ rename_images.py --date-format '%%Y%%m%%d_%%H%%M%%S%%f"'  renames example.jpg to 20200222_123045000_example.jpg
          NOTE that this is the default setting. Also note that even though %%f is microsecond, we convert it to millisecond
        $ rename_images.py --date-format '%%Y-%%m-%%d_%%H-%%M-%%S' renames example.jpg to 2020-02-22_12-30-45_example.jpg
        $ rename_images.py --date-format '%%Y_%%m_%%d'          renames example.jpg to 2020_02_22_example.jpg
""",
    )
    parser.add_argument(
        "--revert",
        action="store_true",
        help="reverts changes for the given directory or file",
    )
    parser.add_argument(
        "--debug",
        action="store_const",
        const=logging.DEBUG,
        default=logging.INFO,
        dest="loglevel",
        help="displays debugging messages",
    )
    parser.add_argument(
        "path",
        nargs="*",
        default=[pathlib.Path().cwd()],
        type=pathlib.Path,
        help="path of image file or directory containing images",
    )

    try:
        args = parser.parse_args()
    except re.error as error:
        logger.error("invalid regex for --pattern: %s", error)
        sys.exit(1)

    # logging settings
    logging.basicConfig(format="%(levelname)s: %(message)s", level=args.loglevel)

    # validate the paths
    for path in args.path:
        if not path.is_dir() and not path.is_file():
            logger.error("'%s' is not a valid path", path)
            sys.exit(1)

    if (
        len(args.date_format) < 4
        or len(args.date_format) > 32
        or "%" not in args.date_format
        or not LEGAL_DATE_FORMAT_CHARS.fullmatch(args.date_format)
    ):
        logger.error(
            "'%s' is not a valid date format. see datetime.strftime()", args.date_format
        )
        sys.exit(1)

    # read cache
    # TODO: maybe use appdirs to find cache_dir: https://github.com/ActiveState/appdirs
    cache_dir = os.environ.get("XDG_CACHE_DIR", pathlib.Path.home().joinpath(".cache"))
    cached_data_file = pathlib.Path(cache_dir).joinpath(CACHE_FILENAME)
    cached_data = {}
    try:
        cached_data = json.loads(cached_data_file.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        pass

    # make it so
    for path in args.path:
        if args.revert:
            revert_path(path, args.recursive, args.dry_run, cached_data)
        else:
            process_path(
                path,
                args.recursive,
                args.pattern,
                args.date_format,
                args.dry_run,
                cached_data,
            )

    # update cache
    cached_data_file.write_text(
        json.dumps(cached_data, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
