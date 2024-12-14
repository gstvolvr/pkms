import frontmatter
from sitecustomize import long_prefix

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import glob
import util
import re
import json



PEOPLE_PATTERN = re.compile(r"""
        (
        \[
            [a-zA-Z\-|\s]+
        \]
        \(

            [\./]+
            people
            [\.a-zA-Z\s\-/0-9%]+
        \)
        )
    """, re.VERBOSE | re.IGNORECASE)

def get_city_state(latitude, longitude):
    """Returns the city and state for a given latitude and longitude."""
    geolocator = Nominatim(user_agent="geoapi")
    try:
        location = geolocator.reverse((latitude, longitude), exactly_one=True)
        if location and location.raw.get('address'):
            address = location.raw['address']
            city = address.get('city') or address.get('town') or address.get('village')
            state = address.get('state')
            return city, state
        return None, None
    except GeocoderTimedOut:
        print("Geocoder service timed out. Try again.")
        return None, None

def init_meta(path: str) -> None:
    with open(path, 'r') as f:
        text = f.read()
        if 'people:' in text and 'locations:' in text:
            print(f'metadata exists for: {path}\n\nskipping...')
            return

    post = fm.read_file(path)
    post['people'] = []
    post['locations'] = []
    post['date'] = util.get_date_from_path(path)

    frontmatter.dump(post, path)

def md_path_to_yaml_path(md_path: str) -> str:
    """Convert markdown path to yaml path

    input: '[First Last](../../../../people/family/First%20Last.md)'
    output: [[../../../../people/family/First Last|First List]]
    """
    return f'[[{get_md_path_value(md_path).replace("%20", " ")}|{get_md_path_key(md_path).replace("%20", " ")}]]'

def get_md_path_value(md_path: str) -> str:
    return md_path.split('(')[1].replace(')', '')

def get_md_path_key(md_path: str) -> str:
    name = md_path.split('/')[-1]
    return name.replace('%20', ' ').replace('.md', '').replace(')', '')


def get_yaml_path_key(yaml_path: str) -> str:
    name = yaml_path.split('/')[-1]
    return name.split('|')[0].replace('.md', '')


def enrich_meta(path: str) -> None:
    """Capture links from the text and add them to the metadata"""

    post_file = fm.read_file(path)
    post = post_file.get('attributes')
    if post is None:
        return

    if post.get('people') is None:
        return

    with open(path, 'r') as f:
        text = f.read()
        people_md = re.findall(PEOPLE_PATTERN, text)
        md_path = {get_md_path_key(p): p for p in people_md}
        yaml_path = {get_yaml_path_key(p): p for p in post['people']}

        md_keys = set(md_path.keys())
        yaml_keys = set(yaml_path.keys())
        missing_keys = md_keys - yaml_keys
        if len(missing_keys) > 0:
            for k in missing_keys:
                this_yaml_path = md_path_to_yaml_path(md_path[k])
                if this_yaml_path not in post['people']:
                    post['people'].append(this_yaml_path)
        post['people'] = list(set(post['people']))
    # TODO: handle updating file
    # frontmatter.dump(post, path)

def read_photo_metadata(path: str):
    meta = {'latitude': None, 'longitude': None, 'people': []}
    mappings = {
        'EXIF:GPSLatitude': 'latitude',
        'EXIF:GPSLongitude': 'longitude',
        'XMP:PersonInImage': 'people',
    }

    with open(path) as f:
        metadata = json.load(f)
        if metadata:
            metadata = metadata.pop()
        for k, v in mappings.items():
            data = metadata.get(k)
            if data is None:
                continue

            if type(meta[v]) == list:
                meta[v].append(data)
            else:
                meta[v] = data
    return meta


if __name__ == '__main__':
    existing_files = glob.glob(f'{util.PENSIEVE_PATH}/*/*/*')
    fm = frontmatter.Frontmatter()
    for i, path in enumerate(existing_files):
        #init_meta(path)
        enrich_meta(path)

    latitude = 42.32586333333333
    longitude = -71.1492695

    city, state = get_city_state(latitude, longitude)
    if city and state:
        print(f"The location is in {city}, {state}.")
