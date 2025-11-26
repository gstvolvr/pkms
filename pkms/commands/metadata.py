import collections
import os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import glob
import time
from pkms import util
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

    fm_dict, body = util.load_frontmatter_and_body(path)
    if fm_dict is None:
        fm_dict = {}
    fm_dict['people'] = []
    fm_dict['locations'] = []
    fm_dict['date'] = util.get_date_from_path(path)

    util.write_frontmatter_and_body(path, fm_dict, body)

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
    fm, body = util.load_frontmatter_and_body(path)
    if fm is None:
        fm = {}

    if 'locations' not in fm or fm['locations'] is None:
        fm['locations'] = []
    elif fm['locations'] != []:
        return

    # Add new cities to the metadata
    print('Actually adding cities: ', cities)
    fm['locations'] = list(set(fm['locations'] + cities))

    # Update the markdown file with the new metadata
    util.write_frontmatter_and_body(path, fm, body)

def enrich_meta_with_people(path: str, photo_metadata: dict = None) -> None:
    """Capture links from the text and add them to the metadata"""

    fm, body = util.load_frontmatter_and_body(path)
    if fm is None:
        return

    if fm.get('people') is None:
        return

    with open(path, 'r') as f:
        text = f.read()
        people_md = re.findall(PEOPLE_PATTERN, text)
        md_path = {get_md_path_key(p): p for p in people_md}
        yaml_path = {get_yaml_path_key(p): p for p in fm['people']}

        md_keys = set(md_path.keys())
        yaml_keys = set(yaml_path.keys())
        missing_keys = md_keys - yaml_keys
        if len(missing_keys) > 0:
            for k in missing_keys:
                this_yaml_path = md_path_to_yaml_path(md_path[k])
                if this_yaml_path not in fm['people']:
                    fm['people'].append(this_yaml_path)
        fm['people'] = list(set(fm['people']))
    # NOTE: This function historically did not write changes back.
    # If you want to persist, uncomment the next line.
    # util.write_frontmatter_and_body(path, fm, body)

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
        current_fm, current_body = util.load_frontmatter_and_body(current_file)
        if current_fm is None:
            current_fm = {}

        current_locations = current_fm.get('locations', [])

        # If locations are empty or missing, check neighbors
        if not current_locations:
            neighbors = []
            current_date = util.get_date_from_path(current_file)
            if i > 0:  # Previous day
                prev_file = files_by_date[sorted_dates[i - 1]]
                prev_fm, _ = util.load_frontmatter_and_body(prev_file)
                if prev_fm is None:
                    prev_fm = {}
                prev_date = util.get_date_from_path(prev_file)
                if current_date and prev_date and abs((current_date - prev_date).days) <= 1:
                    print(f'Previous day: {prev_file}')
                    neighbors.extend(prev_fm.get('locations', []) or [])
            if i < len(sorted_dates) - 1:  # Next day
                next_file = files_by_date[sorted_dates[i + 1]]
                next_fm, _ = util.load_frontmatter_and_body(next_file)
                if next_fm is None:
                    next_fm = {}
                next_date = util.get_date_from_path(next_file)
                if current_date and next_date and abs((current_date - next_date).days) <= 1:
                    print(f'Next day: {next_file}')
                    neighbors.extend(next_fm.get('locations', []) or [])

            # Update current file's locations if neighbors provide a non-empty list
            if neighbors:
                print('neighbors', list(set(neighbors)))
                print(f"Updating locations metadata for: {current_file}")
                current_fm['locations'] = list(set(neighbors))  # Keep unique locations
                util.write_frontmatter_and_body(current_file, current_fm, current_body)

def _build_people_alias_map():
    """Build a case-insensitive alias map for people.

    Returns dict alias_lower -> (person_file_full_path, display_name)
    display_name is derived from the filename (without extension).
    """
    alias_map = {}
    for person_file in util.find_all_files(util.PEOPLE_PATH):
        if not person_file.endswith('.md'):
            continue
        display = os.path.splitext(os.path.basename(person_file))[0]
        # always map the filename itself as an alias
        alias_map[display.lower()] = (person_file, display)
        try:
            fm, _body = util.load_frontmatter_and_body(person_file)
            if isinstance(fm, dict):
                aliases = fm.get('aliases')
                if isinstance(aliases, list):
                    for a in aliases:
                        if isinstance(a, str) and a.strip():
                            alias_map[a.strip().lower()] = (person_file, display)
        except Exception:
            # ignore malformed frontmatter
            pass
    return alias_map


def _flatten_people_from_metadata(meta_people_field):
    """Flatten various shapes of XMP:PersonInImage into a list of plain strings."""
    names = []
    if not meta_people_field:
        return names
    # meta_people_field often becomes a list containing either strings or lists
    stack = [meta_people_field]
    while stack:
        item = stack.pop()
        if isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, str):
            s = item.strip()
            if s:
                names.append(s)
    return names


essentially_space = ' '

def _make_wikilink(note_path: str, person_file: str, display: str) -> str:
    """Construct an Obsidian wikilink [[relative/path|Display]]."""
    note_dir = os.path.dirname(note_path)
    rel = os.path.relpath(person_file, start=note_dir)
    rel = rel.replace('\\', '/')
    return f"[[{rel}|{display}]]"


def load_photo_metadata_into_md_frontmatter():
    # Build alias map once
    people_alias_map = _build_people_alias_map()

    existing_files = glob.glob(f'{util.PENSIEVE_PATH}/*/*/*.md')
    for i, path in enumerate(sorted(existing_files)):
        year, month, date_file_name = path.split('/')[7:]
        day = date_file_name.split('.')[0][-2:]
        photo_metadata_paths = glob.glob(f'{util.PHOTOS_PATH}/{year}/{month}/{day}/*.json')

        # Read current fm/body using util helpers for safe updates
        fm, body = util.load_frontmatter_and_body(path)
        if fm is None:
            fm = {}
        # Normalize people field to list
        existing_people = fm.get('people')
        if existing_people is None:
            existing_people = []
        elif isinstance(existing_people, str):
            existing_people = [existing_people]
        elif not isinstance(existing_people, list):
            existing_people = []

        # 1) Collect city votes as before (but don't early-continue; just conditionally write later)
        cities = collections.defaultdict(int)
        # 2) Collect person names from photos
        photo_person_names = []

        for photo_path in photo_metadata_paths:
            photo_metadata = read_photo_metadata(photo_path)
            # locations
            if 'latitude' in photo_metadata and 'longitude' in photo_metadata:
                lat, lon = photo_metadata['latitude'], photo_metadata['longitude']
                if lat is not None and lon is not None:
                    city, state = get_city_state(lat, lon)
                    if city:
                        cities[city] += 1
            # people
            if 'people' in photo_metadata:
                photo_person_names.extend(_flatten_people_from_metadata(photo_metadata['people']))

        # Prepare new people links
        to_add_people_links = []
        # Resolve existing people to absolute files to avoid duplicates by path
        existing_abs = _resolve_existing_people_files(path, existing_people, people_alias_map)
        seen_links = set(p.strip() for p in existing_people if isinstance(p, str))
        for raw_name in photo_person_names:
            key = raw_name.strip().lower()
            match = people_alias_map.get(key)
            if not match:
                continue
            person_file, display = match
            # Skip if this person file already present regardless of link display/path variations
            if person_file in existing_abs:
                continue
            wikilink = _make_wikilink(path, person_file, display)
            if wikilink not in seen_links:
                to_add_people_links.append(wikilink)
                seen_links.add(wikilink)

        # Update fm if needed
        changed = False
        if to_add_people_links:
            fm['people'] = list(sorted(set(existing_people + to_add_people_links)))
            changed = True

        # Only add locations if none exist yet (preserve old behavior)
        existing_locations = fm.get('locations')
        if (existing_locations is None or existing_locations == []) and cities:
            most_common_city = max(cities, key=cities.get)
            # Store as a wikilink to the location page if desired; keep prior formatting logic minimal
            fm['locations'] = list(set([f"[[{most_common_city}]]"]))
            changed = True

        if changed:
            util.write_frontmatter_and_body(path, fm, body)

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
            # lat, lon = photo_metadata['latitude'], photo_metadata['longitude']
            # if lat is not None and lon is not None:
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
                    time.sleep(0.01)
                    continue
                #     continue


# --- Interactive people-from-photos reviewer (similar to find_links) ---

def _load_processed_people(processed_file: str):
    """Load processed people suggestions as a set of (note_path, person_file).
    If file does not exist, return empty set.
    """
    try:
        if not os.path.exists(processed_file):
            return set()
        with open(processed_file, 'r') as f:
            data = json.load(f)
        # Normalize to tuples
        processed = set()
        for item in data:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                processed.add((item[0], item[1]))
        return processed
    except Exception:
        return set()


def _save_processed_people(processed_file: str, processed: set):
    data = [[note, person] for (note, person) in processed]
    with open(processed_file, 'w') as f:
        json.dump(data, f)


def _count_remaining_people(processed: set) -> int:
    """Count remaining candidate people suggestions not yet processed.

    Scans notes, collects photo-derived candidates, and excludes suggestions when
    the person is already present in fm['people'] (resolved by absolute person file)
    or when the (note_path, person_file) pair has already been processed.
    """
    people_alias_map = _build_people_alias_map()
    existing_files = sorted(glob.glob(f'{util.PENSIEVE_PATH}/*/*/*.md'))
    remaining = 0
    for note_path in existing_files:
        fm, _body = util.load_frontmatter_and_body(note_path)
        if fm is None:
            fm = {}
        existing_people = fm.get('people')
        if existing_people is None:
            existing_people = []
        elif isinstance(existing_people, str):
            existing_people = [existing_people]
        elif not isinstance(existing_people, list):
            existing_people = []
        # Resolve existing entries to absolute person files to avoid path/display dupes
        existing_abs = _resolve_existing_people_files(note_path, existing_people, people_alias_map)
        existing_set = set(p.strip() for p in existing_people if isinstance(p, str))

        candidates = _collect_note_photo_people(note_path, people_alias_map)
        for person_file, _display, wikilink in candidates:
            # Skip if already present by absolute person file
            if person_file in existing_abs:
                continue
            # Also skip if an exact wikilink already exists
            if wikilink in existing_set:
                continue
            if (note_path, person_file) in processed:
                continue
            remaining += 1
    return remaining


def count_candidate_people(processed_file: str = 'processed_people.json') -> int:
    """Return and print the number of candidate people suggestions left to review."""
    processed = _load_processed_people(processed_file)
    remaining = _count_remaining_people(processed)
    print(f"Candidate people left to review: {remaining}")
    return remaining


WIKILINK_RE = re.compile(r"^\[\[([^\]|]+)(?:\|([^\]]+))?\]\]$")


def _resolve_existing_people_files(note_path: str, people_entries: list, people_alias_map: dict) -> set:
    """Resolve existing fm['people'] entries to absolute person file paths.
    Accepts wikilinks with relative paths, plain relative/absolute paths, and name-only wikilinks [[Name]].
    Falls back to alias map when possible. Returns a set of absolute person file paths.
    """
    abs_set = set()
    note_dir = os.path.dirname(note_path)
    for entry in people_entries or []:
        if not isinstance(entry, str):
            continue
        s = entry.strip()
        if not s:
            continue
        abs_path = None
        m = WIKILINK_RE.match(s)
        rel = None
        if m:
            rel = m.group(1)
            disp = m.group(2)
            rel_norm = rel.replace('\\', '/').replace('%20', ' ')
            # If it looks like a path to a file, try resolve
            if '/' in rel_norm or rel_norm.endswith('.md'):
                cand = os.path.normpath(os.path.join(note_dir, rel_norm))
                if os.path.exists(cand):
                    abs_path = cand
                else:
                    alt = os.path.normpath(os.path.join(util.BASE_PATH, rel_norm))
                    if os.path.exists(alt):
                        abs_path = alt
            if abs_path is None:
                # Treat rel_norm as a display/title and try alias map
                key = rel_norm.split('/')[-1].replace('.md', '').lower()
                mapped = people_alias_map.get(key)
                if mapped:
                    abs_path = mapped[0]
        else:
            # Non-wikilink: maybe a path
            if s.endswith('.md') and ('/' in s or '\\' in s):
                rel_norm = s.replace('\\', '/').replace('%20', ' ')
                cand = os.path.normpath(os.path.join(note_dir, rel_norm))
                if os.path.exists(cand):
                    abs_path = cand
                else:
                    alt = os.path.normpath(os.path.join(util.BASE_PATH, rel_norm))
                    if os.path.exists(alt):
                        abs_path = alt
            else:
                # Plain name; try alias map
                key = s.strip('[]').split('|')[0].split('/')[-1].replace('.md', '').lower()
                mapped = people_alias_map.get(key)
                if mapped:
                    abs_path = mapped[0]
        if abs_path:
            abs_set.add(abs_path)
    return abs_set


def _collect_note_photo_people(note_path: str, people_alias_map: dict) -> list:
    """From photo sidecars associated to note_path, collect mapped person candidates.

    Returns a list of tuples (person_file, display, wikilink).
    """
    # Derive year/month/day from note_path similar to load_photo_metadata_into_md_frontmatter
    try:
        year, month, date_file_name = note_path.split('/')[7:]
        day = date_file_name.split('.')[0][-2:]
    except Exception:
        return []
    photo_metadata_paths = glob.glob(f'{util.PHOTOS_PATH}/{year}/{month}/{day}/*.json')

    photo_person_names = []
    for photo_path in photo_metadata_paths:
        photo_metadata = read_photo_metadata(photo_path)
        if 'people' in photo_metadata:
            photo_person_names.extend(_flatten_people_from_metadata(photo_metadata['people']))

    results = []
    seen_pf = set()
    for raw_name in photo_person_names:
        key = raw_name.strip().lower()
        match = people_alias_map.get(key)
        if not match:
            continue
        person_file, display = match
        if person_file in seen_pf:
            continue
        wikilink = _make_wikilink(note_path, person_file, display)
        results.append((person_file, display, wikilink))
        seen_pf.add(person_file)
    return results


def _preview_note_for_people(note_path: str, fm: dict, body: str, proposed_display: str, proposed_link: str) -> None:
    """Print a concise preview of the note before prompting the user.
    Shows filename, current people, and the first few non-empty lines of body.
    """
    note_name = os.path.basename(note_path)
    # Normalize people preview
    ppl = fm.get('people')
    if ppl is None:
        ppl_list = []
    elif isinstance(ppl, str):
        ppl_list = [ppl]
    elif isinstance(ppl, list):
        ppl_list = [p for p in ppl if isinstance(p, str) and p.strip()]
    else:
        ppl_list = []

    print("\n" + "=" * 80)
    print(f"File: {note_name}")
    print(f"Current people: {ppl_list if ppl_list else '[]'}")
    print(f"Proposed: {proposed_display} -> {proposed_link}")
    print("-- Body preview --")
    # Show the first up to 12 non-empty lines from the body for context
    lines = [ln for ln in (body or '').splitlines()]
    shown = 0
    for ln in lines:
        if ln.strip() == '' and shown == 0:
            # skip leading blank lines
            continue
        print(ln)
        shown += 1
        if shown >= 12:
            break
    if shown < len(lines):
        print("... (truncated) ...")
    print("=" * 80)


def prompt_add_people_from_photos(processed_file: str = 'processed_people.json'):
    """Interactively review photo-derived people suggestions per note and prompt to add.

    - Mirrors find_links behavior: y to add, n to skip, q to quit.
    - Records both y and n decisions in processed_file to avoid re-prompting.
    """
    people_alias_map = _build_people_alias_map()
    existing_files = sorted(glob.glob(f'{util.PENSIEVE_PATH}/*/*/*.md'))

    processed = _load_processed_people(processed_file)

    total_candidates = 0
    added = 0
    skipped = 0

    for note_path in existing_files:
        fm, body = util.load_frontmatter_and_body(note_path)
        if fm is None:
            fm = {}
        # Normalize existing people to list of strings
        existing_people = fm.get('people')
        if existing_people is None:
            existing_people = []
        elif isinstance(existing_people, str):
            existing_people = [existing_people]
        elif not isinstance(existing_people, list):
            existing_people = []

        # Build sets for quick contains
        existing_set = set(p.strip() for p in existing_people if isinstance(p, str))
        existing_abs = _resolve_existing_people_files(note_path, existing_people, people_alias_map)

        candidates = _collect_note_photo_people(note_path, people_alias_map)
        for person_file, display, wikilink in candidates:
            # Skip if already present in fm['people'] (by resolved person file path)
            if person_file in existing_abs:
                # also mark processed to avoid future prompts for same person in this note
                processed.add((note_path, person_file))
                continue
            # Skip if processed (y or n) previously
            if (note_path, person_file) in processed:
                continue

            total_candidates += 1
            # Show a preview of the file before prompting
            _preview_note_for_people(note_path, fm, body, display, wikilink)
            resp = input("Add this person to metadata? (y/n/q): ").strip().lower()
            if resp == 'q':
                _save_processed_people(processed_file, processed)
                print(f"Stopped. Added {added}, skipped {skipped}, seen {total_candidates}.")
                return
            if resp == 'y':
                # Append and write
                new_people = list(existing_set)
                new_people.append(wikilink)
                # Keep sorted uniqueness
                fm['people'] = sorted(set(new_people))
                util.write_frontmatter_and_body(note_path, fm, body)
                added += 1
                processed.add((note_path, person_file))
                # Update existing_set so subsequent candidates reflect the change in-memory
                existing_set.add(wikilink)
                print("Added.")
                # remaining = _count_remaining_people(processed)
                # print(f"Remaining candidate people to review: {remaining}")
            else:
                skipped += 1
                processed.add((note_path, person_file))
                print("Skipped.")
                # remaining = _count_remaining_people(processed)
                # print(f"Remaining candidate people to review: {remaining}")

    _save_processed_people(processed_file, processed)
    print(f"Done. Added {added}, skipped {skipped}, reviewed {total_candidates} candidates.")
    remaining = _count_remaining_people(processed)
    print(f"Remaining candidate people to review: {remaining}")

def auto_add_people_from_photos(approved_names_source: str = 'auto_approved_people.txt', processed_file: str = 'processed_people.json') -> None:
    """
    Auto-approve and add specific people (from photo metadata) into notes' YAML frontmatter.

    - Reads a list of approved names from approved_names_source (one per line; '#' comments allowed).
    - Names are matched against any alias of a person (using the same alias map as interactive flow).
    - For matching candidates found in a note's photo-derived suggestions, automatically adds the wikilink
      to fm['people'] without prompting, and records the decision in processed_file to avoid re-prompting later.
    """
    # Build alias map once (alias_lower -> (person_file, display))
    people_alias_map = _build_people_alias_map()

    # Load processed decisions (note_path, person_file)
    processed = _load_processed_people(processed_file)

    # Load approved names
    if not os.path.exists(approved_names_source):
        print(f"Approved names file not found: {approved_names_source}. Nothing to do.")
        return

    with open(approved_names_source, 'r') as f:
        raw_lines = [line.strip() for line in f.readlines()]
    approved_names = [l for l in raw_lines if l and not l.startswith('#')]

    if not approved_names:
        print("Approved names list is empty. Nothing to do.")
        return

    # Resolve approved names to a set of person_file paths via alias map
    approved_person_files = set()
    unresolved = []
    for name in approved_names:
        key = name.strip().lower()
        match = people_alias_map.get(key)
        if match:
            person_file, _display = match
            approved_person_files.add(person_file)
        else:
            unresolved.append(name)

    if unresolved:
        print("Warning: the following approved names did not match any existing person alias:")
        for n in unresolved:
            print(f"  - {n}")

    if not approved_person_files:
        print("No approved names resolved to people files. Nothing to do.")
        return

    existing_files = sorted(glob.glob(f'{util.PENSIEVE_PATH}/*/*/*.md'))

    added = 0
    already_present = 0
    skipped_processed = 0

    for note_path in existing_files:
        fm, body = util.load_frontmatter_and_body(note_path)
        if fm is None:
            fm = {}
        existing_people = fm.get('people')
        if existing_people is None:
            existing_people = []
        elif isinstance(existing_people, str):
            existing_people = [existing_people]
        elif not isinstance(existing_people, list):
            existing_people = []
        existing_set = set(p.strip() for p in existing_people if isinstance(p, str))
        existing_abs = _resolve_existing_people_files(note_path, existing_people, people_alias_map)

        candidates = _collect_note_photo_people(note_path, people_alias_map)
        changed = False
        for person_file, display, wikilink in candidates:
            if person_file not in approved_person_files:
                continue
            # If person already present by path, count as already_present and mark processed
            if person_file in existing_abs:
                already_present += 1
                if (note_path, person_file) not in processed:
                    processed.add((note_path, person_file))
                continue
            if wikilink in existing_set:
                already_present += 1
                if (note_path, person_file) not in processed:
                    processed.add((note_path, person_file))
                continue
            if (note_path, person_file) in processed:
                skipped_processed += 1
                continue

            # Auto-approve: add to fm['people']
            new_people = list(existing_set)
            new_people.append(wikilink)
            fm['people'] = sorted(set(new_people))
            util.write_frontmatter_and_body(note_path, fm, body)
            existing_set.add(wikilink)
            existing_abs.add(person_file)
            processed.add((note_path, person_file))
            added += 1
            changed = True

        # No per-note print needed unless changed; keep output concise
        if changed:
            note_name = os.path.basename(note_path)
            print(f"Updated: {note_name}")

    _save_processed_people(processed_file, processed)
    print(f"Auto-approve complete. Added {added}, already present {already_present}, skipped (already processed) {skipped_processed}.")
    # Show how many candidates remain overall for manual review
    remaining = _count_remaining_people(processed)
    print(f"Remaining candidate people to review interactively: {remaining}")


if __name__ == '__main__':
    # auto_add_people_from_photos()
    prompt_add_people_from_photos()
    # watch out for the use of templates
    # create_notes_based_on_photos()
    # load_photo_metadata_into_md_frontmatter()
    # propagate_location_metadata()


