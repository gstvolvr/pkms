import click
from pkms.core.config import get_config
from pkms.core.utils import find_all_files, get_date_from_path
from pkms.core.frontmatter import load_frontmatter_and_body, write_frontmatter_and_body

def _apply_wipes(fm: dict) -> bool:
    changed = False
    if 'locations' in fm:
        val = fm.get('locations')
        v = str(val).strip()
        if 'miami' in v.lower():
            changed = True
            fm['locations'] = None

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
            for name in remove_set:
                if name in val.strip():
                    fm['people'] = None
                    changed = True
                    continue
    return changed

@click.command('wipe')
@click.option('--year', type=int, help='Year to wipe metadata from')
def wipe(year):
    """Wipe bad metadata from notes."""
    config = get_config()
    count = 0
    updated = 0
    for path in find_all_files(str(config.pensieve_path)):
        if year:
            path_date = get_date_from_path(path)
            if path_date.year > year:
                continue

        if not path.endswith('.md'):
            continue
        count += 1
        try:
            fm, body = load_frontmatter_and_body(path)
            if fm is None:
                continue
            if _apply_wipes(fm):
                write_frontmatter_and_body(path, fm, body)
                click.echo(f"Updated: {path}")
                updated += 1
        except Exception as e:
            click.echo(f"Error processing {path}: {e}", err=True)
    click.echo(f"Scanned {count} markdown files. Updated {updated}.")
