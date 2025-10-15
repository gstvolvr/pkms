"""Vault operations and utilities."""
import glob
import datetime
from pathlib import Path
from typing import Optional


def find_all_files(path: str) -> list[str]:
    """Find all markdown files recursively up to 4 levels deep."""
    files = []
    files.extend(glob.glob(f'{path}/*.md'))
    files.extend(glob.glob(f'{path}/*/*.md'))
    files.extend(glob.glob(f'{path}/*/*/*.md'))
    files.extend(glob.glob(f'{path}/*/*/*/*.md'))
    return files


def get_date_from_path(path: str) -> Optional[datetime.date]:
    """
    Extract date from pensieve file paths following the convention:
        "{base_dir}/{year}/{month}/YYMMDD.md"
    """
    file_name = Path(path).name.replace('.md', '')
    year_prefix = '19' if 'day/19' in path else '20'
    year = year_prefix + file_name[:2]
    month = file_name[2:4].lstrip("0")
    day = file_name[4:].lstrip("0")
    try:
        return datetime.date(int(year), int(month), int(day))
    except Exception as e:
        raise ValueError(f"Couldn't convert {path}: {e}")
