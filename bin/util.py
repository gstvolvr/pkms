import os
import glob
import datetime
from typing import Optional
from pathlib import Path

HOME_PATH = os.path.expanduser('~')
OBSIDIAN_VAULT_NAME = 'vida'
BASE_PATH = f'{HOME_PATH}/obsidian/{OBSIDIAN_VAULT_NAME}'
PENSIEVE_PATH = os.path.join(BASE_PATH, 'pensieve/day')
CONCEPTS_PATH = os.path.join(BASE_PATH, 'concepts')
SUMMARIES_PATH = os.path.join(BASE_PATH, 'summaries')
PHOTOS_PATH = f'{HOME_PATH}/photos'


def get_date_from_path(path: str) -> Optional[datetime.date]:
    """
        Pensieve file paths follow the convention of:
            "{base_dir}/{year}/{month}/YYYYMMDD.md"
    """
    file_name = Path(path).name.replace('.md', '')
    year = '20' + file_name[:2]
    month = file_name[2:4].lstrip("0")
    day = file_name[4:].lstrip("0")
    try:
        return datetime.date(int(year), int(month), int(day))
    except Exception as e:
        raise f'Couldnt convert {path}: {e}'

def find_all_files(path: str):
    files = []

    files.extend(glob.glob(f'{path}/*.md'))
    files.extend(glob.glob(f'{path}/*/*.md'))
    files.extend(glob.glob(f'{path}/*/*/*.md'))
    files.extend(glob.glob(f'{path}/*/*/*/*.md'))

    return files

