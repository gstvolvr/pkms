import os
import re
import json
import glob
import datetime
from typing import Dict, Tuple, List, Optional

from pkms import util

# ------------------------------------------------------------
# Helpers to work with people links and note titles
# ------------------------------------------------------------

WIKILINK_RE = re.compile(r"^\[\[([^\]|]+)(?:\|([^\]]+))?\]\]$")


def _list_markdown_files(base: str) -> List[str]:
    if base == ".":
        return sorted(glob.glob(f"./*.md"))
    return sorted(glob.glob(f"{base}/*/*/*.md"))


def _load_people_alias_map() -> Tuple[Dict[str, Tuple[str, str]], Dict[str, str]]:
    """
    Build two maps for people files:
      1) alias_lower -> (abs_person_file, preferred_display)
      2) abs_person_file -> preferred_display
    Preferred display is ALWAYS the first token of the person file's basename (to avoid nicknames).
    """
    alias_map: Dict[str, Tuple[str, str]] = {}
    file_to_display: Dict[str, str] = {}

    for person_file in util.find_all_files(util.PEOPLE_PATH):
        if not person_file.endswith('.md'):
            continue
        base_display = os.path.splitext(os.path.basename(person_file))[0]
        # Preferred display: first token of filename
        preferred = base_display.split()[0]
        try:
            fm, _body = util.load_frontmatter_and_body(person_file)
        except Exception:
            fm = None
        # Map aliases (full string) as keys to this person file, but do NOT change preferred
        if isinstance(fm, dict):
            aliases = fm.get('aliases')
            if isinstance(aliases, list) and aliases:
                for a in aliases:
                    if isinstance(a, str) and a.strip():
                        alias_map[a.strip().lower()] = (person_file, preferred)
        # Always map the filename (full and first token) as aliases too
        alias_map[base_display.lower()] = (person_file, preferred)
        alias_map[base_display.split()[0].lower()] = (person_file, preferred)
        file_to_display[person_file] = preferred

    return alias_map, file_to_display


def _parse_people_entry(note_path: str, entry: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse a people frontmatter entry and return (abs_person_file, display).
    Supports forms like:
      - [[relative/path/to/person.md|Display]]
      - [[relative/path/to/person.md]]
      - [[Some Person]] (will be treated as a title without a path -> unresolved)
      - plain string path '../../people/X.md' (rare)
    Returns (None, None) if cannot resolve to a person file.
    """
    entry = (entry or '').strip()
    if not entry:
        return None, None

    m = WIKILINK_RE.match(entry)
    rel = None
    display = None
    if m:
        rel = m.group(1)
        display = m.group(2)
    else:
        # Try to accept plain paths
        if entry.endswith('.md') and ('/' in entry or '\\' in entry):
            rel = entry
        else:
            # Can't resolve a non-path, non-wikilink safely
            return None, None

    # Build absolute path
    note_dir = os.path.dirname(note_path)
    rel_norm = rel.replace('\\', '/').replace('%20', ' ')
    abs_path = os.path.normpath(os.path.join(note_dir, rel_norm))

    if not os.path.exists(abs_path):
        # Try resolving relative to base vault if provided as absolute-like from root of vault
        # Best-effort: if path lacks vault prefix, attempt to join with util.BASE_PATH
        abs_alt = os.path.normpath(os.path.join(util.BASE_PATH, rel_norm))
        if os.path.exists(abs_alt):
            abs_path = abs_alt
        else:
            return None, None

    return abs_path, display


def _make_wikilink(note_path: str, abs_person_file: str, display: str) -> str:
    note_dir = os.path.dirname(note_path)
    rel = os.path.relpath(abs_person_file, start=note_dir).replace('\\', '/')
    return f"[[{rel}|{display}]]"


def _desired_title_for(path: str) -> str:
    d = util.get_date_from_path(path)
    if not isinstance(d, datetime.date):
        # Fall back to filename parse without util, just in case
        file_part = os.path.splitext(os.path.basename(path))[0]
        yy, mm, dd = file_part[:2], file_part[2:4], file_part[4:]
        year = int(('19' if path.find('/day/19') != -1 else '20') + yy)
        d = datetime.date(year, int(mm), int(dd))
    weekday = d.strftime('%A')
    month = d.strftime('%B')
    day = d.day
    return f"# {weekday}, {month} {day}"


def _ensure_title(body: str, desired_title: str) -> Tuple[str, bool, Optional[str]]:
    """Ensure the first non-empty line is the desired H1. Returns (new_body, changed, old_title)."""
    lines = body.splitlines()
    # Find first non-empty line index
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    old_title = None
    if idx < len(lines) and lines[idx].lstrip().startswith('#'):
        old_title = lines[idx]
        if lines[idx].strip() == desired_title:
            return body, False, old_title
        lines[idx] = desired_title
        return "\n".join(lines) + ("\n" if body.endswith('\n') else ''), True, old_title
    else:
        # Insert desired title before first content, preserving original spacing
        prefix = "\n".join(lines[:idx])
        suffix = "\n".join(lines[idx:])
        new_body = (prefix + ("\n" if prefix and not prefix.endswith("\n") else "") + desired_title + ("\n\n" if suffix else "\n") + suffix).lstrip("\n")
        return new_body, True, old_title


# ------------------------------------------------------------
# Core standardization logic
# ------------------------------------------------------------

def standardize_people_and_title(path: str, alias_map=None, file_to_display=None, dry_run: bool = False) -> Tuple[bool, Dict[str, object]]:
    """
    Standardize a single note's frontmatter people list, sort locations, and H1 title.
    Returns (changed, log_dict)
    log_dict has keys: 'people_before', 'people_after', 'locations_before', 'locations_after', 'title_before', 'title_after'
    Set dry_run=True to compute proposed changes without writing to disk.
    """
    fm, body = util.load_frontmatter_and_body(path)
    if fm is None:
        fm = {}

    # Date synchronization
    date_from_path = util.get_date_from_path(path)
    date_from_fm = fm.get('date')
    changed_date = False
    if date_from_path and str(date_from_path) != str(date_from_fm):
        changed_date = True

    # Normalize people
    people = fm.get('people')
    if people is None:
        people_list: List[str] = []
    elif isinstance(people, str):
        people_list = [people]
    elif isinstance(people, list):
        # Coerce to list of strings
        people_list = [p for p in people if isinstance(p, str) and p.strip()]
    else:
        people_list = []

    # Normalize locations
    locations = fm.get('locations')
    if locations is None:
        locations_list: List[str] = []
    elif isinstance(locations, str):
        locations_list = [locations]
    elif isinstance(locations, list):
        locations_list = [l for l in locations if isinstance(l, str) and l.strip()]
    else:
        locations_list = []

    if alias_map is None or file_to_display is None:
        alias_map, file_to_display = _load_people_alias_map()

    resolved: List[Tuple[str, str]] = []  # (abs_file, display_current)
    for entry in people_list:
        abs_file, disp = _parse_people_entry(path, entry)
        if abs_file is None:
            # not resolvable; try alias lookup using raw text to map to a person file
            key = entry.strip().strip('[]').split('|')[0].split('/')[-1].replace('.md', '').lower()
            mapped = alias_map.get(key)
            if mapped:
                abs_file = mapped[0]
                disp = None
            else:
                continue
        resolved.append((abs_file, disp or ''))

    # Deduplicate by person file and standardize display to preferred first name
    # Allow duplicate first names as long as they reference different person files
    seen_files = set()
    standardized_links: List[str] = []
    for abs_file, _disp in resolved:
        if abs_file in seen_files:
            continue
        preferred = file_to_display.get(abs_file)
        if not preferred:
            # fallback to filename first token
            preferred = os.path.splitext(os.path.basename(abs_file))[0].split()[0]
        seen_files.add(abs_file)
        link = _make_wikilink(path, abs_file, preferred)
        standardized_links.append(link)

    # Sort for deterministic output (people and locations)
    standardized_links = sorted(standardized_links)
    sorted_locations = sorted(locations_list)

    # Title processing
    desired_title = _desired_title_for(path)
    new_body, body_changed, old_title = _ensure_title(body, desired_title)

    # Determine changes
    changed_people = (standardized_links != people_list)
    changed_locations = (sorted_locations != locations_list)
    changed = changed_people or changed_locations or body_changed or changed_date

    log = {
        'people_before': people_list,
        'people_after': standardized_links,
        'locations_before': locations_list,
        'locations_after': sorted_locations,
        'title_before': old_title,
        'title_after': desired_title if body_changed else old_title,
        'date_before': str(date_from_fm) if date_from_fm else None,
        'date_after': str(date_from_path) if date_from_path else None,
    }

    if changed and not dry_run:
        if changed_date:
            fm['date'] = date_from_path
        fm['people'] = standardized_links if standardized_links else None
        fm['locations'] = sorted_locations if sorted_locations else None
        util.write_frontmatter_and_body(path, fm, new_body)

    return changed, log


# ------------------------------------------------------------
# Batch runners and interactive review
# ------------------------------------------------------------

PROCESSED_FILE = 'processed_review_metadata.json'

essentially_space = ' '

def run_auto() -> None:
    alias_map, file_to_display = _load_people_alias_map()
    files = _list_markdown_files(util.PENSIEVE_PATH)
    updated = 0
    scanned = 0
    for path in files:
        scanned += 1
        changed, log = standardize_people_and_title(path, alias_map, file_to_display)
        if changed:
            updated += 1
            print(f"Updated: {path}")
            if log.get('people_before') != log.get('people_after'):
                print(f"  people: {log['people_before']} -> {log['people_after']}")
            if log.get('locations_before') != log.get('locations_after'):
                print(f"  locations: {log.get('locations_before')} -> {log.get('locations_after')}")
            if log.get('date_before') != log.get('date_after'):
                print(f"  date: {log.get('date_before')} -> {log.get('date_after')}")
            if log['title_before'] != log['title_after']:
                print(f"  title: {log['title_before']} -> {log['title_after']}")
    print(f"Scanned {scanned} files. Updated {updated}.")


def _load_processed() -> set:
    try:
        if not os.path.exists(PROCESSED_FILE):
            return set()
        with open(PROCESSED_FILE, 'r') as f:
            data = json.load(f)
        return set(data)
    except Exception:
        return set()


def _save_processed(s: set) -> None:
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(list(s), f)


def _preview_changes(path: str, log: Dict[str, object]) -> None:
    print(f"\nFile: {path}")
    if log.get('people_before') != log.get('people_after'):
        print(f"People before: {log['people_before']}")
        print(f"People after:  {log['people_after']}")
    if log.get('locations_before') != log.get('locations_after'):
        print(f"Locations before: {log.get('locations_before')}")
        print(f"Locations after:  {log.get('locations_after')}")
    if log.get('date_before') != log.get('date_after'):
        print(f"Date before: {log.get('date_before')}")
        print(f"Date after:  {log.get('date_after')}")
    if log['title_before'] != log['title_after']:
        print(f"Title before: {log['title_before']}")
        print(f"Title after:  {log['title_after']}")


def _count_remaining_interactive() -> int:
    processed = _load_processed()
    files = _list_markdown_files(util.PENSIEVE_PATH)
    alias_map, file_to_display = _load_people_alias_map()
    remaining = 0
    for path in files:
        if path in processed:
            continue
        # Dry-run to see if there would be changes
        fm, body = util.load_frontmatter_and_body(path)
        if fm is None:
            fm = {}

        # Date check
        date_from_path = util.get_date_from_path(path)
        date_from_fm = fm.get('date')
        will_change_date = False
        if date_from_path and str(date_from_path) != str(date_from_fm):
            will_change_date = True

        # People
        before_people = fm.get('people')
        if isinstance(before_people, str):
            people_list = [before_people]
        elif isinstance(before_people, list):
            people_list = [p for p in before_people if isinstance(p, str) and p.strip()]
        else:
            people_list = []
        # Locations
        before_locations = fm.get('locations')
        if isinstance(before_locations, str):
            locations_list = [before_locations]
        elif isinstance(before_locations, list):
            locations_list = [l for l in before_locations if isinstance(l, str) and l.strip()]
        else:
            locations_list = []

        desired_title = _desired_title_for(path)
        _, body_changed, _ = _ensure_title(body, desired_title)

        # If either people normalization would change, locations need sorting, or title needs change, count it
        # Build standardized set to compare roughly (without writing)
        resolved = []
        for entry in people_list:
            abs_file, _disp = _parse_people_entry(path, entry)
            if abs_file is None:
                key = entry.strip().strip('[]').split('|')[0].split('/')[-1].replace('.md', '').lower()
                mapped = alias_map.get(key)
                if mapped:
                    abs_file = mapped[0]
                else:
                    continue
            resolved.append(abs_file)
        will_change_people = len(set(resolved)) != len(people_list)
        if people_list:
            # Also check if displays already match preferred
            for abs_file in set(resolved):
                preferred = file_to_display.get(abs_file, os.path.splitext(os.path.basename(abs_file))[0].split()[0])
                relink = _make_wikilink(path, abs_file, preferred)
                if relink not in people_list:
                    will_change_people = True
                    break
        # Locations need change if sorted order differs
        will_change_locations = (sorted(locations_list) != locations_list)

        if body_changed or will_change_people or will_change_locations or will_change_date:
            remaining += 1
    return remaining


def run_interactive() -> None:
    processed = _load_processed()
    files = _list_markdown_files(util.PENSIEVE_PATH)
    alias_map, file_to_display = _load_people_alias_map()

    apply_all = False
    updated = 0
    for path in files:
        if path in processed:
            continue
        # Dry-run to preview changes
        changed, log = standardize_people_and_title(path, alias_map, file_to_display, dry_run=True)
        if not changed:
            processed.add(path)
            continue
        _preview_changes(path, log)
        do_apply = apply_all
        if not apply_all:
            resp = input("Apply these changes? (y=yes/n=no/a=all/q=quit): ").strip().lower()
            if resp == 'q':
                break
            if resp == 'a':
                apply_all = True
                do_apply = True
            elif resp == 'y':
                do_apply = True
            else:
                do_apply = False
        if do_apply:
            # Apply for real
            standardize_people_and_title(path, alias_map, file_to_display, dry_run=False)
            updated += 1
        processed.add(path)
        # remaining = _count_remaining_interactive()
        # print(f"Remaining files needing review: {remaining}")

    _save_processed(processed)
    print(f"Interactive review complete. Updated {updated} files.")


# ------------------------------------------------------------
# Outlier detection based on co-occurrence
# ------------------------------------------------------------
import itertools
from statistics import mean

OUTLIERS_PROCESSED_FILE = 'processed_review_outliers.json'


def _resolve_people_entries(note_path: str, people_list: List[str], alias_map: Dict[str, Tuple[str, str]]):
    """Resolve frontmatter people entries to absolute person files.
    Returns list of tuples (abs_person_file, original_entry).
    """
    resolved = []
    for entry in people_list:
        abs_file, _disp = _parse_people_entry(note_path, entry)
        if abs_file is None:
            key = entry.strip().strip('[]').split('|')[0].split('/')[-1].replace('.md', '').lower()
            mapped = alias_map.get(key)
            if mapped:
                abs_file = mapped[0]
            else:
                continue
        resolved.append((abs_file, entry))
    return resolved


essentially_space = ' '

def _compute_cooccurrence(files: List[str], alias_map: Dict[str, Tuple[str, str]]):
    """Compute global co-occurrence counts, per-note resolved people, and per-person appearances.
    Returns (co_counts, note_people_map, appearances) where:
      - co_counts: dict[frozenset({pf1, pf2})] -> int
      - note_people_map: dict[note_path] -> list of abs person files
      - appearances: dict[abs_person_file] -> int (number of notes the person appears in)
    """
    co_counts: Dict[frozenset, int] = {}
    note_people_map: Dict[str, List[str]] = {}
    appearances: Dict[str, int] = {}
    for path in files:
        fm, _body = util.load_frontmatter_and_body(path)
        if fm is None:
            fm = {}
        ppl = fm.get('people')
        if ppl is None:
            people_list: List[str] = []
        elif isinstance(ppl, str):
            people_list = [ppl]
        elif isinstance(ppl, list):
            people_list = [p for p in ppl if isinstance(p, str) and p.strip()]
        else:
            people_list = []
        resolved_pairs = _resolve_people_entries(path, people_list, alias_map)
        abs_people = sorted({pf for pf, _orig in resolved_pairs})
        note_people_map[path] = abs_people
        # Count appearances once per note per person
        for pf in abs_people:
            appearances[pf] = appearances.get(pf, 0) + 1
        if len(abs_people) >= 2:
            for a, b in itertools.combinations(abs_people, 2):
                key = frozenset((a, b))
                co_counts[key] = co_counts.get(key, 0) + 1
    return co_counts, note_people_map, appearances


def _generate_outlier_suggestions(
    co_counts: Dict[frozenset, int],
    note_people_map: Dict[str, List[str]],
    file_to_display: Dict[str, str],
    appearances: Dict[str, int],
    min_appearances: int = 10,
    min_co: int = 2,
    min_associated_in_group: int = 2,
):
    """Yield suggestions based on association counts, not probabilities.
    A person p is an outlier in a note if:
      - appearances[p] >= min_appearances
      - In the current note's group, p historically co-occurs (co_counts >= min_co)
        with at most 1 of the other members (i.e., assoc_count <= 1)
      - And at least one other member has assoc_count >= min_associated_in_group (group cohesion)
    Suggestion payload includes: assoc_count and others_assoc for transparency.
    """
    suggestions = []
    for note_path, group in note_people_map.items():
        # Need at least 3 people in the note to evaluate "more than 1 person"
        if len(group) < 3:
            continue
        # Precompute association counts per member within this group
        assoc_counts = {}
        for p in group:
            cnt = 0
            for q in group:
                if p == q:
                    continue
                if co_counts.get(frozenset((p, q)), 0) >= min_co:
                    cnt += 1
            assoc_counts[p] = cnt
        # Ensure there is at least one cohesive other member
        if not any(v >= min_associated_in_group for v in assoc_counts.values()):
            continue
        for p in group:
            ap = appearances.get(p, 0)
            if ap < min_appearances:
                continue
            if assoc_counts.get(p, 0) <= 1:
                display = file_to_display.get(p, os.path.splitext(os.path.basename(p))[0].split()[0])
                suggestions.append({
                    'note_path': note_path,
                    'person_file': p,
                    'display': display,
                    'assoc_count': assoc_counts.get(p, 0),
                    'others_assoc': [assoc_counts[q] for q in group if q != p],
                    'appearances': ap,
                })
    return suggestions


def _load_processed_outliers() -> set:
    try:
        if not os.path.exists(OUTLIERS_PROCESSED_FILE):
            return set()
        with open(OUTLIERS_PROCESSED_FILE, 'r') as f:
            data = json.load(f)
        return set((item[0], item[1]) for item in data if isinstance(item, list) and len(item) == 2)
    except Exception:
        return set()


def _save_processed_outliers(processed: set) -> None:
    with open(OUTLIERS_PROCESSED_FILE, 'w') as f:
        json.dump([[note, person] for (note, person) in processed], f)


def _count_remaining_outliers(min_appearances: int = 10, min_co: int = 2, min_associated_in_group: int = 2) -> int:
    files = _list_markdown_files(util.PENSIEVE_PATH)
    alias_map, file_to_display = _load_people_alias_map()
    co_counts, note_people_map, appearances = _compute_cooccurrence(files, alias_map)
    suggestions = _generate_outlier_suggestions(
        co_counts, note_people_map, file_to_display, appearances,
        min_appearances=min_appearances, min_co=min_co, min_associated_in_group=min_associated_in_group
    )
    processed = _load_processed_outliers()
    remaining = 0
    for s in suggestions:
        key = (s['note_path'], s['person_file'])
        if key not in processed:
            remaining += 1
    return remaining


def find_outlier_people(min_appearances: int = 10, min_co: int = 2, min_associated_in_group: int = 2) -> List[dict]:
    """Compute and print outlier person suggestions across the vault (association-count heuristic). Does not modify files."""
    files = _list_markdown_files(util.PENSIEVE_PATH)
    alias_map, file_to_display = _load_people_alias_map()
    co_counts, note_people_map, appearances = _compute_cooccurrence(files, alias_map)
    suggestions = _generate_outlier_suggestions(
        co_counts, note_people_map, file_to_display, appearances,
        min_appearances=min_appearances, min_co=min_co, min_associated_in_group=min_associated_in_group
    )
    processed = _load_processed_outliers()
    print(f"Found {len(suggestions)} outlier suggestions ({len([s for s in suggestions if (s['note_path'], s['person_file']) not in processed])} pending).")
    for s in suggestions:
        note_name = os.path.basename(s['note_path'])
        print(
            f"Note {note_name}: suggest removing {s['display']} "
            f"(appearances={s['appearances']}, assoc_count={s.get('assoc_count')}, "
            f"others_assoc={','.join(str(x) for x in s.get('others_assoc', []))})"
        )
    return suggestions


def _remove_person_from_note(note_path: str, person_file: str, alias_map: Dict[str, Tuple[str, str]]) -> bool:
    """Remove entries in fm['people'] that resolve to person_file. Returns True if changed and written."""
    fm, body = util.load_frontmatter_and_body(note_path)
    if fm is None:
        return False
    ppl = fm.get('people')
    if ppl is None:
        return False
    if isinstance(ppl, str):
        people_list = [ppl]
    elif isinstance(ppl, list):
        people_list = [p for p in ppl if isinstance(p, str) and p.strip()]
    else:
        return False
    # Keep those not matching person_file
    kept = []
    for entry in people_list:
        abs_file, _disp = _parse_people_entry(note_path, entry)
        if abs_file is None:
            key = entry.strip().strip('[]').split('|')[0].split('/')[-1].replace('.md', '').lower()
            mapped = alias_map.get(key)
            if mapped:
                abs_file = mapped[0]
        if abs_file == person_file:
            continue
        kept.append(entry)
    if kept == people_list:
        return False
    fm['people'] = kept if kept else None
    util.write_frontmatter_and_body(note_path, fm, body)
    return True


def review_outliers_interactive(min_appearances: int = 10, min_co: int = 2, min_associated_in_group: int = 2) -> None:
    """Interactive review of outlier deletions with y/n/q prompts (association-count heuristic)."""
    files = _list_markdown_files(util.PENSIEVE_PATH)
    alias_map, file_to_display = _load_people_alias_map()
    co_counts, note_people_map, appearances = _compute_cooccurrence(files, alias_map)
    suggestions = _generate_outlier_suggestions(
        co_counts, note_people_map, file_to_display, appearances,
        min_appearances=min_appearances, min_co=min_co, min_associated_in_group=min_associated_in_group
    )
    processed = _load_processed_outliers()

    total = 0
    deleted = 0
    skipped = 0

    for s in suggestions:
        key = (s['note_path'], s['person_file'])
        if key in processed:
            continue
        total += 1
        note_name = os.path.basename(s['note_path'])
        print(f"\nNote: {note_name}")
        print(
            f"Suggest deleting person: {s['display']} "
            f"(appearances={s['appearances']}, assoc_count={s.get('assoc_count')}, "
            f"others_assoc={','.join(str(x) for x in s.get('others_assoc', []))})"
        )
        resp = input("Delete this person from metadata? (y/n/q): ").strip().lower()
        if resp == 'q':
            break
        elif resp == 'y':
            if _remove_person_from_note(s['note_path'], s['person_file'], alias_map):
                print("Deleted.")
                deleted += 1
            else:
                print("Nothing changed (entry not found).")
            processed.add(key)
        else:
            skipped += 1
            processed.add(key)
        remaining = _count_remaining_outliers(min_appearances=min_appearances, min_co=min_co, min_associated_in_group=min_associated_in_group)
        print(f"Remaining outlier suggestions to review: {remaining}")

    _save_processed_outliers(processed)
    print(f"Interactive outlier review complete. Deleted {deleted}, skipped {skipped}, seen {total}.")


# ------------------------------------------------------------
# Duplicate YAML review
# ------------------------------------------------------------

def _find_duplicate_yaml_files() -> List[str]:
    """Find markdown files with more than one YAML frontmatter block."""
    duplicates = []
    files = _list_markdown_files(util.PENSIEVE_PATH)
    for path in files:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            if content.count('---') > 3:
                parts = content.split('---')
                if len(parts) > 3 and parts[0].strip() == '' and parts[2].strip() != '':
                    duplicates.append(path)
        except Exception as e:
            print(f"Error processing {path}: {e}")
    return duplicates

def review_duplicate_yaml() -> None:
    """Interactively review and fix files with duplicate YAML frontmatter."""
    files = _find_duplicate_yaml_files()
    if not files:
        print("No files with duplicate YAML frontmatter found.")
        return

    print(f"Found {len(files)} files with duplicate YAML frontmatter.")
    apply_all = False
    fixed_count = 0

    for path in files:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {path}: {e}")
            continue

        parts = content.split('---')
        if len(parts) <= 3:
            continue

        # Keep the first YAML block and the content that follows it, up to the next '---'.
        new_content = f"---{parts[1]}---{parts[2]}"

        print(f"\nFile: {path}")
        print("\nCurrent content:")
        print("="*20)
        print(content)
        print("="*20)
        print("\nProposed changes:")
        print("="*20)
        print(new_content)
        print("="*20)


        do_apply = apply_all
        if not apply_all:
            resp = input("Apply these changes? (y=yes/n=no/a=all/q=quit): ").strip().lower()
            if resp == 'q':
                break
            if resp == 'a':
                apply_all = True
                do_apply = True
            elif resp == 'y':
                do_apply = True
            else:
                do_apply = False
        
        if do_apply:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Fixed: {path}")
                fixed_count += 1
            except Exception as e:
                print(f"Error writing to {path}: {e}")

    print(f"\nDuplicate YAML review complete. Fixed {fixed_count} files.")


if __name__ == '__main__':
    import sys
    argv = sys.argv
    # Common params for outlier commands
    def _parse_outlier_params(args):
        # Defaults align with association-count heuristic
        min_app = 10
        min_co = 2
        min_assoc = 2
        for a in args:
            if a.startswith('--min-appearances='):
                try:
                    min_app = int(a.split('=', 1)[1])
                except Exception:
                    pass
            elif a.startswith('--min-co='):
                try:
                    min_co = int(a.split('=', 1)[1])
                except Exception:
                    pass
            elif a.startswith('--min-associated='):
                try:
                    min_assoc = int(a.split('=', 1)[1])
                except Exception:
                    pass
            # Backward-compat: accept old flags but ignore their values
            elif a.startswith('--prob-threshold=') or a.startswith('--contrast-threshold='):
                continue
        return min_app, min_co, min_assoc

    if '--interactive' in argv or '-i' in argv:
        run_interactive()
    elif '--count' in argv:
        print(f"Pending interactive items: {_count_remaining_interactive()}")
    elif '--duplicate-yaml' in argv:
        review_duplicate_yaml()
    elif any(a.startswith('--outliers') for a in argv):
        min_app, min_co, min_assoc = _parse_outlier_params(argv)
        if any(a.startswith('--outliers-interactive') for a in argv):
            review_outliers_interactive(min_appearances=min_app, min_co=min_co, min_associated_in_group=min_assoc)
        elif any(a.startswith('--outliers-count') for a in argv):
            print(f"Pending outlier suggestions: {_count_remaining_outliers(min_appearances=min_app, min_co=min_co, min_associated_in_group=min_assoc)}")
        else:
            find_outlier_people(min_appearances=min_app, min_co=min_co, min_associated_in_group=min_assoc)
    else:
        run_auto()
