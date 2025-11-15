"""General utility functions."""
import datetime
import glob
from pathlib import Path
from typing import Optional


def get_date_from_path(path: str) -> Optional[datetime.date]:
    """
        Pensieve file paths follow the convention of:
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
        raise f"Couldn't convert {path}: {e}"

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

def get_city_state(latitude, longitude):
    geolocator = Nominatim(user_agent="pkms")
    try:
        location = geolocator.reverse((latitude, longitude), exactly_one=True)
        address = location.raw['address']
        city = address.get('city', '')
        state = address.get('state', '')
        return city, state
    except GeocoderTimedOut:
        return None, None

def find_all_files(path: str):
    files = []

    files.extend(glob.glob(f'{path}/*.md'))
    files.extend(glob.glob(f'{path}/*/*.md'))
    files.extend(glob.glob(f'{path}/*/*/*.md'))
    files.extend(glob.glob(f'{path}/*/*/*/*.md'))

    return files
