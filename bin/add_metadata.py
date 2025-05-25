import collections
import frontmatter
import os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import glob
import time
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
    geolocator = Nominatim(user_agent="geoapi")
    for i in range(3):
        try:
            location = geolocator.reverse((latitude, longitude), exactly_one=True)
            if location and location.raw.get('address'):
                address = location.raw['address']
                city = address.get('city') or address.get('town') or address.get('village')
                state = address.get('state')
                return city, state
            return None, None
        except GeocoderTimedOut:
            print(f"Geocoder service timed out. Try again. Attempt number: {i+1}")
            time.sleep(1.0)
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


def enrich_meta_with_locations(path: str, cities: list) -> None:
    """Add a list of cities to the metadata under the 'locations' attribute."""
    with open(path, 'r') as f:
        post = frontmatter.load(f)

    if 'locations' not in post or post['locations'] is None:
        post['locations'] = []
    elif not post['locations'] == []:
        return


    # Add new cities to the metadata
    print('Actually adding cities: ', cities)
    post['locations'] = list(set(post['locations'] + cities))

    # Update the markdown file with the new metadata
    frontmatter.dump(post, path)

def enrich_meta_with_people(path: str, photo_metadata: dict = None) -> None:
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


def propagate_location_metadata():
    existing_files = glob.glob(f'{util.PENSIEVE_PATH}/*/*/*.md')

    files_by_date = {file_path.split('/')[-1][:6]: file_path for file_path in existing_files}

    # Process and share 'locations' metadata
    sorted_dates = sorted(files_by_date.keys())
    for i, date in enumerate(sorted_dates):
        current_file = files_by_date[date]

        # Read the frontmatter of the current file
        with open(current_file, 'r') as f:
            current_post = frontmatter.load(f)

        current_locations = current_post.get('locations', [])

        # If locations are empty or missing, check neighbors
        if not current_locations:
            neighbors = []
            current_date = util.get_date_from_path(current_file)
            if i > 0:  # Previous day
                prev_file = files_by_date[sorted_dates[i - 1]]
                prev_date = util.get_date_from_path(prev_file)
                if current_date and prev_date and abs((current_date - prev_date).days) <= 1:
                    print(f'Previous day: {prev_file}')
                    with open(prev_file, 'r') as prev_f:
                        prev_post = frontmatter.load(prev_f)
                        neighbors.extend(prev_post.get('locations', []) or [])
            if i < len(sorted_dates) - 1:  # Next day
                next_file = files_by_date[sorted_dates[i + 1]]
                next_date = util.get_date_from_path(next_file)
                if current_date and next_date and abs((current_date - next_date).days) <= 1:
                    print(f'Next day: {next_file}')
                    with open(next_file, 'r') as next_f:
                        next_post = frontmatter.load(next_f)
                        neighbors.extend(next_post.get('locations', []) or [])

            # Update current file's locations if neighbors provide a non-empty list
            if neighbors:
                print('neighbors', list(set(neighbors)))
                print(f"Updating locations metadata for: {current_file}")
                current_post['locations'] = list(set(neighbors))  # Keep unique locations
                frontmatter.dump(current_post, current_file)

def load_photo_metadata_into_md_frontmatter():
    existing_files = glob.glob(f'{util.PENSIEVE_PATH}/*/*/*.md')
    for i, path in enumerate(sorted(existing_files)):
        year, month, date_file_name = path.split('/')[7:]
        day = date_file_name.split('.')[0][-2:]
        photo_metadata_paths = glob.glob(f'{util.PHOTOS_PATH}/{year}/{month}/{day}/*.json')
        with open(path, 'r') as f:
            fmt = frontmatter.load(f)
            if fmt.get('locations') is not None and fmt.get('locations') != []:
                # print(f'Already have a location for: {path}, {fmt.get("locations")}')
                continue

        # keep track of the most common cities.
        # since I get photos from other people in my library I only want to keep track of the most common cases
        cities = collections.defaultdict(int)
        for photo_path in photo_metadata_paths:
            photo_metadata = read_photo_metadata(photo_path)
            if 'latitude' in photo_metadata and 'longitude' in photo_metadata:
                lat, lon = photo_metadata['latitude'], photo_metadata['longitude']
                if lat is not None and lat is not None:
                    city, state = get_city_state(lat, lon)
                    if city:
                        cities[city] += 1
        if cities:
            most_common_city = max(cities, key=cities.get)
            print(most_common_city)
            enrich_meta_with_locations(path, [f'{[[most_common_city]]}'.replace("'", '')])

def create_notes_based_on_photos():
    """
    If we have metadata from photos then we should create daily notes even if we don't currently have any written content in them
    """
    photo_files = sorted(glob.glob(f'{util.PHOTOS_PATH}/*/*/*/*.json'), reverse=True)
    existing_files = glob.glob(f'{util.PENSIEVE_PATH}/*/*/*.md')

    for photo_path in photo_files:
        # Extract metadata from photo
        photo_metadata = read_photo_metadata(photo_path)

        # Check if latitude and longitude are present
        if 'latitude' in photo_metadata and 'longitude' in photo_metadata:
            # print(photo_path)
            lat, lon = photo_metadata['latitude'], photo_metadata['longitude']
            if lat is not None and lon is not None:
                # Parse the date information from the photo path
                year, month, day = photo_path.split('/')[-4:-1]
                if int(year) < 1992:
                    continue
                day = day.split('.')[0]  # Remove file extension

                # Construct the file path under PENSIEVE_PATH
                note_path = f"{util.PENSIEVE_PATH}/{year}/{month}/{year[2:]}{month}{day}.md"

                # Ensure the directory exists before creating the file
                os.makedirs(os.path.dirname(note_path), exist_ok=True)

                # print(note_path)
                # Write an empty markdown file if it doesn't already exist
                if not os.path.exists(note_path):
                    print(f"Created note file: {note_path}")
                    with open(note_path, 'w') as note_file:
                        time.sleep(1)
                        continue
                    #     continue


if __name__ == '__main__':
    # watch out for the use of templates
    # create_notes_based_on_photos()
    load_photo_metadata_into_md_frontmatter()
    propagate_location_metadata()
