import frontmatter

import util
import glob
import json
from add_photos import get_photo_files
from add_metadata import PEOPLE_PATTERN
from bin.scan_for_people import find_all_people


# TODO: suggest creating pensieve files based on photo metadata

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

def yaml_to_first_name(path: str) -> str:
    names = path.split('|')
    if len(names) > 1:
        return names[1].split(' ')[0]
    return names[0].replace(']', '').replace('[', '')


def main():
    existing_files = glob.glob(f'{util.PENSIEVE_PATH}/*/*/*')
    first_name_to_yaml_path = {}

    names_to_path = find_all_people()
    fm = frontmatter.Frontmatter()
    for i, path in enumerate(existing_files):
        post = fm.read_file(path)
        attributes = post.get('attributes', {})
        if not attributes:
            continue
        existing_people_yaml = attributes.get('people', [])
        if not existing_people_yaml:
            continue
        for p in existing_people_yaml:
            first_name = yaml_to_first_name(p)
            if first_name not in first_name_to_yaml_path:
                first_name_to_yaml_path[first_name] = p
    print(first_name_to_yaml_path)

    for i, path in enumerate(existing_files):
        photo_metadata_paths = list(get_photo_files(path, ['json']))
        post = fm.read_file(path)
        existing_people_yaml = post.get('attributes', {}).get('people', [])
        existing_first_names = [yaml_to_first_name(path) for path in existing_people_yaml]
        # existing_people_yaml
        # TODO: convert iCloud person into yaml path
        for photo_metadata_path in photo_metadata_paths:
            metadata = read_photo_metadata(photo_metadata_path)
            print(metadata)
            for people in metadata['people']:
                for person in people:
                    first_name = person.split(' ')[0]
                    if first_name in existing_first_names:
                        continue
                    if first_name == 'Gustavo':
                        continue
                    print(first_name, names_to_path.get(first_name), first_name_to_yaml_path.get(first_name))
                    print()
        if i > 10:
            break

if __name__ == '__main__':
    main()

