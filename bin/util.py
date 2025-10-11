import os
import glob
import datetime
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import yaml

HOME_PATH = os.path.expanduser('~')
OBSIDIAN_VAULT_NAME = 'vida'
BASE_PATH = f'{HOME_PATH}/obsidian/{OBSIDIAN_VAULT_NAME}'
PENSIEVE_PATH = os.path.join(BASE_PATH, 'pensieve/day')
PEOPLE_PATH = os.path.join(BASE_PATH, 'people')
LOCATIONS_PATH = os.path.join(BASE_PATH, 'locations')
ENTITIES_PATHS = [PEOPLE_PATH, LOCATIONS_PATH]
CONCEPTS_PATH = os.path.join(BASE_PATH, 'concepts')
SUMMARIES_PATH = os.path.join(BASE_PATH, 'summaries')
PHOTOS_PATH = f'{HOME_PATH}/photos'


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

def find_all_files(path: str):
    files = []

    files.extend(glob.glob(f'{path}/*.md'))
    files.extend(glob.glob(f'{path}/*/*.md'))
    files.extend(glob.glob(f'{path}/*/*/*.md'))
    files.extend(glob.glob(f'{path}/*/*/*/*.md'))

    return files


# Reusable frontmatter helpers for markdown files

def load_frontmatter_and_body(path: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Load YAML frontmatter and body from a markdown file.
    Returns (frontmatter_dict_or_None, body_text).
    - If no or malformed frontmatter, returns (None, full_content).
    - If YAML exists but isn't a dict, treat as None to avoid damage.
    """
    with open(path, 'r') as f:
        content = f.read()

    if not content.startswith('---'):
        return None, content

    parts = content.split('---', 2)
    if len(parts) < 3:
        # Malformed; treat as no frontmatter
        return None, content

    _start, fm_text, body = parts
    try:
        fm = yaml.safe_load(fm_text) or {}
        if not isinstance(fm, dict):
            return None, content
        return fm, body.lstrip('\n')
    except Exception:
        # If YAML fails, do not modify file
        return None, content


def dump_frontmatter(fm: Dict[str, Any]) -> str:
    """Dump a frontmatter dict to YAML string (no leading/trailing ---)."""
    return yaml.safe_dump(fm, sort_keys=False, default_flow_style=False).strip() + "\n"


def write_frontmatter_and_body(path: str, fm: Dict[str, Any], body: str) -> None:
    """Write a markdown file from fm dict and body text using --- separators."""
    fm_text = dump_frontmatter(fm)
    # Ensure a single blank line between frontmatter and body unless body begins with a newline
    content = f"---\n{fm_text}---\n\n{body}" if body and not body.startswith('\n') else f"---\n{fm_text}---\n{body}"
    with open(path, 'w') as f:
        f.write(content)

