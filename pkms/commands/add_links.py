import os
import re
from typing import List, Tuple

import pytest
import yaml
import json
import util


def get_aliases_from_file(file_path):
    """Extract aliases from the YAML frontmatter of a markdown file using util helpers."""
    print(f'Looking for alias of: {file_path}')
    try:
        fm, _ = util.load_frontmatter_and_body(file_path)
        if not isinstance(fm, dict):
            return []
        aliases = fm.get('aliases')
        if isinstance(aliases, list):
            return aliases
        return []
    except Exception as e:
        print(f"Error reading or parsing {file_path}: {e}")
        return []


def find_alias_map(source_dirs):
    alias_map = {}  # Map aliases to their source file

    for source_dir in source_dirs:
        for source_file in util.find_all_files(source_dir):
            if source_file.endswith(".md"):
                source_path = os.path.join(source_dir, source_file)
                aliases = get_aliases_from_file(source_path)
                for alias in aliases:
                    if alias in alias_map:
                        raise Exception(
                            f"Duplicate alias found: '{alias}' in '{source_path}' and '{alias_map[alias]}'"
                        )
                    alias_map[alias] = source_path
    return alias_map


def _find_ignored_spans(content: str) -> List[Tuple[int, int]]:
    """Return spans of text that should be ignored when suggesting links.

    Ignores:
    - Wiki links: [[...]]
    - Markdown links: [text](url)
    - URLs in plain text (http/https, www.) and autolinks like <http://...>
    - File paths in plain text (Unix-like starting with /, Windows-like C:\\, or any token containing path separators)
    """
    spans: List[Tuple[int, int]] = []

    # 1) [[...]] wiki links
    for m in re.finditer(r"\[\[[^\]]*?\]\]", content):
        spans.append((m.start(), m.end()))

    # 2) [text](...)
    for m in re.finditer(r"\[[^\]]*?\]\([^\)]*?\)", content):
        spans.append((m.start(), m.end()))

    # 3) Autolinks <http://...> or <mailto:...>
    for m in re.finditer(r"<(?:https?://|mailto:)[^\s>]+>", content):
        spans.append((m.start(), m.end()))

    # 4) Bare URLs (http/https) and www.*
    for m in re.finditer(r"\bhttps?://[^\s)\]>]+", content):
        spans.append((m.start(), m.end()))
    for m in re.finditer(r"\bwww\.[^\s)\]>]+", content):
        spans.append((m.start(), m.end()))

    # 5) File/path-like tokens
    #    - Unix-like absolute paths starting with '/'
    for m in re.finditer(r"/(?:[^\s\]\)\}>]+)", content):
        spans.append((m.start(), m.end()))
    #    - Windows drive paths like C:\foo\bar or with forward slashes
    for m in re.finditer(r"[A-Za-z]:[\\/][^\s\]\)\}>]+", content):
        spans.append((m.start(), m.end()))
    #    - Generic path-ish tokens that contain a slash or backslash (to catch relative paths like assets/img.png)
    #      Avoid matching markdown link syntax by excluding closing bracket/paren and whitespace
    for m in re.finditer(r"\b[^\s\[\(]*[\\/][^\s\]\)\}>]+", content):
        spans.append((m.start(), m.end()))

    # Merge overlapping spans for faster checks
    if not spans:
        return spans
    spans.sort()
    merged: List[Tuple[int, int]] = []
    cur_s, cur_e = spans[0]
    for s, e in spans[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    merged.append((cur_s, cur_e))
    return merged


def _is_in_spans(idx: int, spans: List[Tuple[int, int]]) -> bool:
    for s, e in spans:
        if s <= idx < e:
            return True
    return False


def _section_prefix(content: str, pos: int) -> str:
    """Return the nearest preceding markdown heading as the section prefix."""
    lines = content[:pos].splitlines()
    for line in reversed(lines):
        if line.strip().startswith('#'):
            return line.strip()
    return "(no section)"


def _context_snippet(content: str, start: int, end: int, window: int = 40) -> str:
    pre_start = max(0, start - window)
    post_end = min(len(content), end + window)
    pre = content[pre_start:start]
    mid = content[start:end]
    post = content[end:post_end]
    # collapse newlines for display brevity
    snippet = pre.replace('\n', ' ') + '[' + mid + ']' + post.replace('\n', ' ')
    return snippet


def find_potential_links(target_dir, alias_map):
    """Find per-occurrence potential links by searching for aliases in target files, ignoring text already in links."""
    potentials = []  # (target_path, source_path, alias, start_idx, section_prefix, snippet)

    for target_file in util.find_all_files(target_dir):
        if target_file.endswith(".md"):
            target_path = os.path.join(target_dir, target_file)
            with open(target_path, 'r') as f:
                content = f.read()
                ignored = _find_ignored_spans(content)
                for alias, source_path in alias_map.items():
                    # word boundary-ish match; escape alias
                    pattern = re.compile(rf"\b{re.escape(alias)}\b")
                    for m in pattern.finditer(content):
                        s, e = m.start(), m.end()
                        if _is_in_spans(s, ignored):
                            continue
                        section = _section_prefix(content, s)
                        snippet = _context_snippet(content, s, e)
                        potentials.append((target_path, source_path, alias, s, section, snippet))
    # Sort by file then position
    potentials.sort(key=lambda x: (x[0], x[3]))
    return potentials


def _load_processed(processed_links_file: str):
    if not os.path.exists(processed_links_file):
        return set()
    with open(processed_links_file, 'r') as f:
        raw = json.load(f)
    processed = set()
    for item in raw:
        t = tuple(item)
        # Support old 3-tuple format by padding with None for position
        if len(t) == 3:
            target_path, source_path, alias = t
            processed.add((target_path, source_path, alias, None))
        elif len(t) >= 4:
            processed.add((t[0], t[1], t[2], t[3]))
    return processed


def _save_processed(processed_links_file: str, processed: set):
    # Store as list for JSON; normalize to 4-item lists
    data = []
    for item in processed:
        target_path, source_path, alias, pos = item
        data.append([target_path, source_path, alias, pos])
    with open(processed_links_file, 'w') as f:
        json.dump(data, f)


def count_candidate_links(processed_links_file: str = 'processed_links.json') -> int:
    """Return the number of candidate link occurrences that remain to be reviewed.

    This counts potential alias occurrences across pensieve files, excluding those
    already recorded in processed_links.json. A processed entry with pos=None is
    treated as a global skip for that alias→source within the target file.
    """
    alias_map = find_alias_map(util.ENTITIES_PATHS)
    potentials = find_potential_links(util.PENSIEVE_PATH, alias_map)
    processed_links = _load_processed(processed_links_file)

    remaining = 0
    for target_path, source_path, alias, pos, _section, _snippet in potentials:
        if (target_path, source_path, alias, pos) in processed_links or (
            target_path, source_path, alias, None
        ) in processed_links:
            continue
        remaining += 1

    # Also print for convenient CLI usage
    print(f"Remaining candidate links to review: {remaining}")
    return remaining


def _count_remaining_from(potentials, processed_links: set) -> int:
    """Compute remaining candidates using in-memory state without re-reading disk."""
    remaining = 0
    for target_path, source_path, alias, pos, _section, _snippet in potentials:
        if (target_path, source_path, alias, pos) in processed_links or (
            target_path, source_path, alias, None
        ) in processed_links:
            continue
        remaining += 1
    return remaining


def main():
    """Main function to organize Obsidian links per occurrence with context, ignoring existing links."""
    processed_links_file = 'processed_links.json'
    processed_links = _load_processed(processed_links_file)

    alias_map = find_alias_map(util.ENTITIES_PATHS)
    potentials = find_potential_links(util.PENSIEVE_PATH, alias_map)
    print(f"Found {len(potentials)} potential link occurrences.")

    current_file = None
    current_content = None

    for target_path, source_path, alias, pos, section, snippet in potentials:
        # Use None for pos when matching legacy entries
        if (target_path, source_path, alias, pos) in processed_links or (
            target_path, source_path, alias, None
        ) in processed_links:
            continue

        if current_file != target_path:
            # Commit previous file if needed and load new file content
            if current_file is not None and current_content is not None:
                with open(current_file, 'w') as wf:
                    wf.write(current_content)
            with open(target_path, 'r') as rf:
                current_content = rf.read()
            current_file = target_path

        target_filename = os.path.basename(target_path)
        source_filename = os.path.basename(source_path)
        source_page = os.path.splitext(source_filename)[0]

        print(f"\nFile: {target_filename}")
        print(f"Section: {section}")
        print(f"Context: {snippet}")
        print(f"Suggest: '{alias}' -> '{source_filename}'")
        user_input = input("Create this link here? (y/n/q): ")
        if user_input.lower() == 'q':
            break

        # Recompute ignored spans and find the next valid occurrence to be safe
        if user_input.lower() == 'y':
            ignored = _find_ignored_spans(current_content)
            pattern = re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)")
            replaced = False
            for m in pattern.finditer(current_content):
                s, e = m.start(), m.end()
                if _is_in_spans(s, ignored):
                    continue
                # Approximate match to the planned occurrence: choose the first not-yet-processed
                # Since we iterate in sorted order, the first match corresponds to this suggestion
                link_text = f"[[{source_page}|{alias}]]"
                current_content = current_content[:s] + link_text + current_content[e:]
                replaced = True
                break
            if replaced:
                print("Link created.")
                processed_links.add((target_path, source_path, alias, pos))
                remaining = _count_remaining_from(potentials, processed_links)
                print(f"Remaining candidate links to review: {remaining}")
            else:
                print("Could not insert link (no matching occurrence found). Skipped.")
                processed_links.add((target_path, source_path, alias, pos))
                remaining = _count_remaining_from(potentials, processed_links)
                print(f"Remaining candidate links to review: {remaining}")
        else:
            print("Link skipped.")
            # Record a global skip for this alias→source in this file by using pos=None
            processed_links.add((target_path, source_path, alias, None))
            remaining = _count_remaining_from(potentials, processed_links)
            print(f"Remaining candidate links to review: {remaining}")

    # Write the last file content if any changes were made
    if current_file is not None and current_content is not None:
        with open(current_file, 'w') as wf:
            wf.write(current_content)
    _save_processed(processed_links_file, processed_links)


def test_get_aliases_from_file():
    aliases = get_aliases_from_file("/Users/Home/obsidian/vida/people/family/Courtney Oliver.md")
    assert len(aliases) > 1


def test_find_potential_links():
    # Basic smoke test that function runs and returns a list
    potentials = find_potential_links(util.PENSIEVE_PATH, find_alias_map(util.ENTITIES_PATHS))
    assert isinstance(potentials, list)


if __name__ == "__main__":
    main()
    # count_candidate_links()