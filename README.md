# Rename Images with Date Photo Taken

Renames visual media files such as images and videos according to their date of creation

## features

This tool looks into metadata of image files to find the date they were created and allows users to rename the file using the date of creation

- supports \*.jpeg, \*.heic and \*.mov files
  - reads EXIF, HEIF metadata to find the date the file was created
- customizable - user can specify what to rename and how it will be renamed
  - see `--pattern` and `--date-format` options
- dry-run
- revert operation for when the user wants to undo changes
- recurse into directories

## installation

use poetry to install this package

this application also depends on [mediainfo](https://mediaarea.net/en/MediaInfo/Download) library being installed

``` shell
# arch linux
pacman -S python-poetry libmediainfo

# debian / ubuntu
apt install python3-poetry mediainfo

# download this code
git clone https://github.com/paulo-erichsen/rename-images.git
cd rename-images

# install the venv
poetry install

# run the tool
poetry run rename-images --help
```

## usage

``` shell
rename_images.py --help
rename_images.py --dry-run [path] # path of directory containing images
```

## examples

say the exif file had the following date of creation:

- exif:DateTimeOriginal: 2022:02:26 20:22:13
- exif:SubSecTimeOriginal: 203

| command                                           | before                       | after                                   | comment                                                                         |
|---------------------------------------------------|------------------------------|-----------------------------------------|---------------------------------------------------------------------------------|
| `rename-images`                                   | IMG_2001.jpg                 | 20220226_202213203.jpg                  | matches and replaces `IMG_\d{4}` by default                                     |
| `rename-images`                                   | IMG_2001_family_at_beach.jpg | 20220226_202213203_family_at_beach.jpg  | keeps filename descriptions, portion that didn't match                          |
| `rename-images --date-format '%Y-%m-%d_%H-%M-%S'` | IMG_2001_family_at_beach.jpg | 2022-02-26_20-22-13_family_at_beach.jpg | configure the format of the date to use when renaming                           |
| `rename-images --pattern 'FOOBAR\d{4}'`           | FOOBAR9901.JPG               | 20220226_202213203.JPG                  | we can specify a pattern that when matched will be replaced by the date created |

## TODO

- [ ] add support for \*.mp4
- [ ] add tests
