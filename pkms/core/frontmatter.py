"""Frontmatter utilities for markdown files."""
import yaml
from typing import Optional, Tuple, Dict, Any


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
    except Exception as e:
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
