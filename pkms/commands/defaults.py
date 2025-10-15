"""Commands for applying default people/locations based on residence metadata."""
import click
import glob
import datetime
from pathlib import Path
from pkms.core import get_config, load_frontmatter_and_body, write_frontmatter_and_body, get_date_from_path
from pkms.core.vault import find_all_files
from pkms.core.residence import (
    ResidenceCache,
    parse_date,
    get_default_people_for_date,
    get_default_locations_for_date,
    should_add_default_people,
    should_add_default_locations,
)


@click.group()
def defaults():
    """Apply default people/locations based on cohabitation and residence."""
    pass


@defaults.command('apply')
@click.option('--people/--no-people', default=True, help='Apply default people')
@click.option('--locations/--no-locations', default=True, help='Apply default locations')
@click.option('--dry-run', is_flag=True, help='Preview changes without applying')
@click.option('--force', is_flag=True, help='Add defaults even if people/locations already exist')
def apply_defaults(people, locations, dry_run, force):
    """Apply default people/locations to daily notes based on residence metadata.

    Looks for:
    - People with 'cohabitated_start' and optional 'cohabitated_end'
    - Locations with 'lived_start' and optional 'lived_end'

    Only adds defaults to notes that don't already have that person/location.
    """
    config = get_config()
    files = sorted(glob.glob(f'{config.pensieve_path}/*/*/*.md'))

    # Load residence data once (single pass!)
    click.echo("Loading residence metadata...")
    cache = ResidenceCache(config.people_path, config.locations_path)
    click.echo(f"  Found {cache.get_people_with_cohabitation()} people with cohabitation dates")
    click.echo(f"  Found {cache.get_locations_with_residence()} locations with residence dates\n")

    updates = {
        'people_added': 0,
        'locations_added': 0,
        'notes_updated': 0,
        'skipped': 0,
    }

    for file_path in files:
        try:
            # Get date from file path
            date = get_date_from_path(file_path)
            if not date:
                updates['skipped'] += 1
                continue

            # Load frontmatter
            fm, body = load_frontmatter_and_body(file_path)
            if fm is None:
                fm = {}

            changed = False
            changes_desc = []

            # Handle people
            existing_people = []
            if people:
                existing_people = fm.get('people')
                if existing_people is None:
                    existing_people = []
                elif isinstance(existing_people, str):
                    existing_people = [existing_people]
                elif not isinstance(existing_people, list):
                    existing_people = []

                # Get default people for this date (fast - uses cache)
                default_people = get_default_people_for_date(cache, date)

                # Determine what to add
                if force:
                    to_add_people = default_people
                else:
                    to_add_people = should_add_default_people(existing_people, default_people)

                if to_add_people:
                    fm['people'] = sorted(set(existing_people + to_add_people))
                    updates['people_added'] += len(to_add_people)
                    changed = True
                    changes_desc.append(f"+{len(to_add_people)} people")

            # Handle locations
            existing_locations = []
            if locations:
                existing_locations = fm.get('locations')
                if existing_locations is None:
                    existing_locations = []
                elif isinstance(existing_locations, str):
                    existing_locations = [existing_locations]
                elif not isinstance(existing_locations, list):
                    existing_locations = []

                # Get default locations for this date (fast - uses cache)
                default_locations = get_default_locations_for_date(cache, date)

                # Determine what to add
                if force:
                    to_add_locations = default_locations
                else:
                    to_add_locations = should_add_default_locations(existing_locations, default_locations)

                if to_add_locations:
                    fm['locations'] = sorted(set(existing_locations + to_add_locations))
                    updates['locations_added'] += len(to_add_locations)
                    changed = True
                    changes_desc.append(f"+{len(to_add_locations)} locations")

            # Write changes
            if changed:
                if (len(existing_people) > 0 or len(existing_locations) > 0) and date.year > 2010:
                    # click.echo(f"Not updating {file_path} due to existing people: {', '.join(changes_desc)}")
                    # click.echo(f"{body}")
                    continue
                elif dry_run:
                    click.echo(f"Would update {file_path}: {', '.join(changes_desc)}")
                else:
                    write_frontmatter_and_body(file_path, fm, body)
                    if updates['notes_updated'] % 100 == 0:
                        click.echo(f"Updated {updates['notes_updated']} notes...")

                updates['notes_updated'] += 1

        except Exception as e:
            click.echo(f"Error processing {file_path}: {e}", err=True)
            updates['skipped'] += 1

    # Summary
    click.echo("\n✓ Summary:")
    if dry_run:
        click.echo(f"  Would update {updates['notes_updated']} notes (dry run)")
    else:
        click.echo(f"  Updated {updates['notes_updated']} notes")
    if people:
        click.echo(f"  Added {updates['people_added']} people references")
    if locations:
        click.echo(f"  Added {updates['locations_added']} location references")
    if updates['skipped'] > 0:
        click.echo(f"  Skipped {updates['skipped']} files")


@defaults.command('show')
@click.argument('date_str')
def show_defaults(date_str):
    """Show what defaults would apply for a specific date (YYYY-MM-DD)."""
    config = get_config()

    # Parse date
    date = parse_date(date_str)
    if not date:
        click.echo(f"Invalid date format: {date_str}. Use YYYY-MM-DD", err=True)
        return

    # Load cache once
    cache = ResidenceCache(config.people_path, config.locations_path)

    # Get defaults
    default_people = get_default_people_for_date(cache, date)
    default_locations = get_default_locations_for_date(cache, date)

    click.echo(f"\n📅 Defaults for {date_str}\n")

    if default_people:
        click.echo("👥 Cohabitating people:")
        for person in default_people:
            # Extract display name
            if '|' in person:
                name = person.split('|')[-1].strip(']')
            else:
                name = person.strip('[]').split('/')[-1].replace('.md', '')
            click.echo(f"  - {name}")
    else:
        click.echo("👥 No cohabitating people")

    if default_locations:
        click.echo("\n📍 Lived-in locations:")
        for location in default_locations:
            # Extract display name
            if '|' in location:
                name = location.split('|')[-1].strip(']')
            else:
                name = location.strip('[]').split('/')[-1].replace('.md', '')
            click.echo(f"  - {name}")
    else:
        click.echo("\n📍 No lived-in locations")


@defaults.command('stats')
def defaults_stats():
    """Show statistics about residence metadata coverage."""
    config = get_config()

    # Load cache once (single pass!)
    cache = ResidenceCache(config.people_path, config.locations_path)

    # Get total counts
    people_files = [f for f in find_all_files(str(config.people_path)) if f.endswith('.md')]
    location_files = [f for f in find_all_files(str(config.locations_path)) if f.endswith('.md')]

    # Check current defaults
    today = datetime.date.today()
    current_people = cache.get_cohabitating_people(today)
    current_locations = cache.get_lived_in_locations(today)

    click.echo("\n📊 Residence Metadata Statistics\n")
    click.echo(f"People with cohabitation dates: {cache.get_people_with_cohabitation()}/{len(people_files)}")
    click.echo(f"Locations with residence dates: {cache.get_locations_with_residence()}/{len(location_files)}")
    click.echo(f"\nCurrently (as of {today}):")
    click.echo(f"  Cohabitating people: {len(current_people)}")
    for person_file, display in current_people:
        click.echo(f"    - {display}")
    click.echo(f"  Lived-in locations: {len(current_locations)}")
    for location_file, display in current_locations:
        click.echo(f"    - {display}")
