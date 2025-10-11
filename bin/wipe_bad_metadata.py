import os
from typing import Dict, Any

import util


def _apply_wipes(fm: Dict[str, Any]) -> bool:
    """Apply wipe rules to frontmatter in place. Return True if changes were made."""
    changed = False

    # 1) location: if value is 'Miami' or '[[Miami]]', set to None
    if 'locations' in fm:
        val = fm.get('locations')
        v = str(val).strip()
        if 'miami' in v.lower():
            changed = True
            fm['locations'] = None

    # 2) people: remove 'Courtney' and 'Luisa'. If list becomes empty, set to None.
    if 'people' in fm:
        val = fm.get('people')
        remove_set = {"Courtney", "Luisa"}
        if isinstance(val, list):
            for name in remove_set:
                if name in str(val):
                    fm['people'] = None
                    changed = True
                    continue
        elif isinstance(val, str):
            # Handle single string case: wipe if matches target names
            for name in remove_set:
                if name in val.strip():
                    fm['people'] = None
                    changed = True
                    continue

    return changed




def process_file(path: str) -> bool:
    """Process a single markdown file. Returns True if file was modified."""
    fm, body = util.load_frontmatter_and_body(path)
    if fm is None:
        return False

    if '[[Courtney Oliver]]' not in (fm.get('people', []) or []):
        return False

    print(path)
    print(body)
    print('before', fm)
    changed = _apply_wipes(fm)
    if not changed:
        return False

    print('after', fm)
    util.write_frontmatter_and_body(path, fm, body)
    return True


def main():
    base_dir = util.PENSIEVE_PATH
    count = 0
    updated = 0

    for path in util.find_all_files(base_dir):
        path_date = util.get_date_from_path(path)
        if path_date.year > 2010:
            continue

        if not path.endswith('.md'):
            continue
        count += 1
        try:
            if process_file(path):
                print(f"Updated: {path}")
                updated += 1
                # break
        except Exception as e:
            print(f"Error processing {path}: {e}")

    print(f"Scanned {count} markdown files. Updated {updated}.")


if __name__ == '__main__':
    main()
