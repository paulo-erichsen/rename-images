import pathlib
import re
import rename_images
import pytest

IMAGES_PATH = pathlib.Path(__file__).parent / "images"


def test_help_text_appears(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["rename-images", "--help"])
    with pytest.raises(SystemExit):
        rename_images.main()
    assert "usage: rename-images" in capsys.readouterr().out


@pytest.mark.parametrize(
    "file_before, filename_pattern, date_format, recursive, expected_files_after",
    [
        (
            "jpg/Canon_40D.jpg",
            rename_images.DEFAULT_PATTERN_NAME_TO_REPLACE,
            rename_images.DEFAULT_DATE_FORMAT,
            False,
            {
                pathlib.PosixPath("jpg/Canon_40D.jpg"): pathlib.PosixPath(
                    "jpg/20080530_155601000_Canon_40D.jpg"
                )
            },
        ),
        (
            "jpg/Canon_40D.jpg",
            re.compile("Canon", flags=re.IGNORECASE),
            rename_images.DEFAULT_DATE_FORMAT,
            False,
            {
                pathlib.PosixPath("jpg/Canon_40D.jpg"): pathlib.PosixPath(
                    "jpg/20080530_155601000_40D.jpg"
                )
            },
        ),
        (
            "jpg/Canon_40D.jpg",
            re.compile(r"Canon_\d{2}D", flags=re.IGNORECASE),
            rename_images.DEFAULT_DATE_FORMAT,
            False,
            {
                pathlib.PosixPath("jpg/Canon_40D.jpg"): pathlib.PosixPath(
                    "jpg/20080530_155601000.jpg"
                )
            },
        ),
        # (
        #     "jpg/Canon_40D.jpg",
        #     re.compile(".*", flags=re.IGNORECASE),  # FIXME: this matches the extension
        #     rename_images.DEFAULT_DATE_FORMAT,  #        we probably don't want to throw away the extension
        #     False,
        #     {
        #         pathlib.PosixPath("jpg/Canon_40D.jpg"): pathlib.PosixPath(
        #             "jpg/20080530_155601000.jpg"
        #         )
        #     },
        # ),
        (
            "jpg/Canon_40D.jpg",
            rename_images.DEFAULT_PATTERN_NAME_TO_REPLACE,
            "%Y-%m-%d_%H-%M-%S",
            False,
            {
                pathlib.PosixPath("jpg/Canon_40D.jpg"): pathlib.PosixPath(
                    "jpg/2008-05-30_15-56-01_Canon_40D.jpg"
                )
            },
        ),
        (
            "jpg/Canon_40D.jpg",
            rename_images.DEFAULT_PATTERN_NAME_TO_REPLACE,
            "%Y%m%d-%H%M%S",
            False,
            {
                pathlib.PosixPath("jpg/Canon_40D.jpg"): pathlib.PosixPath(
                    "jpg/20080530-155601_Canon_40D.jpg"
                )
            },
        ),
        (
            "jpg/",
            rename_images.DEFAULT_PATTERN_NAME_TO_REPLACE,
            "%Y%m%d-%H%M%S",
            False,
            {
                pathlib.PosixPath("jpg/Canon_40D.jpg"): pathlib.PosixPath(
                    "jpg/20080530-155601_Canon_40D.jpg"
                ),
                pathlib.PosixPath("jpg/sanyo-vpcg250.jpg"): pathlib.PosixPath(
                    "jpg/19980101-000000_sanyo-vpcg250.jpg"
                ),
                pathlib.PosixPath("jpg/Kodak_CX7530.jpg"): pathlib.PosixPath(
                    "jpg/20050813-094723_Kodak_CX7530.jpg"
                ),
            },
        ),
        (
            ".",
            rename_images.DEFAULT_PATTERN_NAME_TO_REPLACE,
            rename_images.DEFAULT_DATE_FORMAT,
            True,
            {
                pathlib.PosixPath("DSCN0042.jpg"): pathlib.PosixPath(
                    "20081022_170007000.jpg"
                ),
                pathlib.PosixPath("Ricoh_Caplio_RR330.jpg"): pathlib.PosixPath(
                    "20040831_195258000_Ricoh_Caplio_RR330.jpg"
                ),
                pathlib.PosixPath("jpg/Canon_40D.jpg"): pathlib.PosixPath(
                    "jpg/20080530_155601000_Canon_40D.jpg"
                ),
                pathlib.PosixPath("jpg/sanyo-vpcg250.jpg"): pathlib.PosixPath(
                    "jpg/19980101_000000000_sanyo-vpcg250.jpg"
                ),
                pathlib.PosixPath("jpg/Kodak_CX7530.jpg"): pathlib.PosixPath(
                    "jpg/20050813_094723345_Kodak_CX7530.jpg"
                ),
                pathlib.PosixPath("heic/sample1.heic"): pathlib.PosixPath(
                    "heic/20221230_123045555_sample1.heic"
                ),
                pathlib.PosixPath("heic/example.heic"): pathlib.PosixPath(
                    "heic/20221116_112859008_example.heic"
                ),
            },
        ),
    ],
)
# TODO: add ids to parametrize
def test_rename_image(
    file_before, filename_pattern, date_format, recursive, expected_files_after
):
    cached_data = {}
    renamed_files = {}
    filename = pathlib.Path(file_before)
    rename_images.process_path(
        IMAGES_PATH / filename,
        recursive,
        filename_pattern,
        date_format,
        True,  # dry_run
        cached_data,
        renamed_files,
    )
    renamed_files = {
        key.relative_to(IMAGES_PATH): value.relative_to(IMAGES_PATH)
        for key, value in renamed_files.items()
    }
    assert renamed_files == expected_files_after


# TODO: add tests for revert - single file, directory of files, recursion
