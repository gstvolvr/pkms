"""Vault statistics and analytics."""
import click
import glob
import collections
import datetime
import os
from pathlib import Path
from pkms.core import get_config, load_frontmatter_and_body, find_all_files, get_date_from_path


def count_notes(path: Path) -> int:
    """Count markdown files in path."""
    return len(list(path.rglob('*.md')))


def get_people_frequency(pensieve_path: Path) -> dict:
    """Get frequency of people mentions across notes."""
    files = glob.glob(f'{pensieve_path}/*/*/*.md')
    people_count = collections.Counter()

    for file_path in files:
        fm, _ = load_frontmatter_and_body(file_path)
        if fm and 'people' in fm:
            people = fm['people']
            if isinstance(people, str):
                people = [people]
            if isinstance(people, list):
                for person in people:
                    # Extract display name from wikilink
                    if isinstance(person, str):
                        if '|' in person:
                            name = person.split('|')[-1].strip(']')
                        else:
                            name = person.strip('[]').split('/')[-1].replace('.md', '')
                        people_count[name] += 1

    return dict(people_count)


def get_locations_frequency(pensieve_path: Path) -> dict:
    """Get frequency of location mentions across notes."""
    files = glob.glob(f'{pensieve_path}/*/*/*.md')
    location_count = collections.Counter()

    for file_path in files:
        fm, _ = load_frontmatter_and_body(file_path)
        if fm and 'locations' in fm:
            locations = fm['locations']
            if isinstance(locations, str):
                locations = [locations]
            if isinstance(locations, list):
                for loc in locations:
                    if isinstance(loc, str):
                        name = loc.strip('[]')
                        location_count[name] += 1

    return dict(location_count)


def get_photo_coverage(pensieve_path: Path, photos_path: Path) -> dict:
    """Calculate photo coverage statistics."""
    notes_files = glob.glob(f'{pensieve_path}/*/*/*.md')
    total_notes = len(notes_files)

    notes_with_photos = 0
    for file_path in notes_files:
        # Extract date from path
        parts = file_path.split('/')
        year, month = parts[-3], parts[-2]
        date = parts[-1].split('.')[0][-2:]

        # Check if photos exist for this date
        photo_dir = photos_path / year / month / date
        if photo_dir.exists() and any(photo_dir.iterdir()):
            notes_with_photos += 1

    return {
        'total_notes': total_notes,
        'notes_with_photos': notes_with_photos,
        'coverage_pct': (notes_with_photos / total_notes * 100) if total_notes > 0 else 0
    }


def _build_people_alias_map(people_path: Path) -> dict:
    """Build a map from aliases (lowercase) to (person_file, display_name, all_aliases).

    Returns:
        dict: alias_lower -> (person_file, display_name, list_of_all_aliases)
    """
    alias_map = {}

    for person_file in find_all_files(str(people_path)):
        if not person_file.endswith('.md'):
            continue

        display = os.path.splitext(os.path.basename(person_file))[0]
        aliases = [display]  # filename is always an alias

        try:
            fm, _body = load_frontmatter_and_body(person_file)
            if isinstance(fm, dict) and 'aliases' in fm:
                alias_list = fm.get('aliases')
                if isinstance(alias_list, list):
                    aliases.extend([a for a in alias_list if isinstance(a, str) and a.strip()])
        except Exception:
            pass

        # Map each alias to this person
        for alias in aliases:
            alias_lower = alias.strip().lower()
            if alias_lower in alias_map:
                # Duplicate alias detected
                existing_file, existing_display, _ = alias_map[alias_lower]
                if existing_file != person_file:
                    # Different person files have the same alias - store both for warning
                    if not isinstance(alias_map[alias_lower], list):
                        alias_map[alias_lower] = [alias_map[alias_lower]]
                    alias_map[alias_lower].append((person_file, display, aliases))
            else:
                alias_map[alias_lower] = (person_file, display, aliases)

    return alias_map


def _resolve_person_file(person_name: str, people_path: Path) -> tuple:
    """Resolve a person name (which could be an alias) to their person file.

    Args:
        person_name: Name or alias to search for
        people_path: Path to people directory

    Returns:
        (person_file, display_name, all_aliases) or (None, None, None) if not found
        or raises ValueError if duplicate aliases are found
    """
    alias_map = _build_people_alias_map(people_path)
    person_lower = person_name.strip().lower()

    if person_lower not in alias_map:
        return None, None, None

    match = alias_map[person_lower]

    # Check if it's a duplicate alias (stored as list)
    if isinstance(match, list):
        click.echo(f"\n⚠️  Warning: '{person_name}' matches multiple people:", err=True)
        for person_file, display, _ in match:
            click.echo(f"   - {display} ({person_file})", err=True)
        raise ValueError(f"Ambiguous name: '{person_name}' matches multiple people")

    return match


def get_person_timeline(pensieve_path: Path, people_path: Path, person_name: str, group_by: str = 'month') -> tuple:
    """Get timeline of mentions for a specific person using alias resolution.

    Args:
        pensieve_path: Path to pensieve directory
        people_path: Path to people directory
        person_name: Name or alias of person to track
        group_by: How to group data ('year', 'month', 'quarter')

    Returns:
        (timeline_dict, resolved_display_name, all_aliases) where timeline has time periods as keys
    """
    # Resolve the person name to their file using aliases
    person_file, display_name, all_aliases = _resolve_person_file(person_name, people_path)

    if person_file is None:
        return {}, None, None

    files = glob.glob(f'{pensieve_path}/*/*/*.md')
    timeline = collections.defaultdict(int)

    for file_path in files:
            debug = '931110' in file_path or '250913' in file_path
        # try:
            # Get date from file path
            date = get_date_from_path(file_path)
            if not date:
                continue

            # Check if person is mentioned
            fm, _ = load_frontmatter_and_body(file_path)
            if not fm or 'people' not in fm:
                continue

            people = fm['people']
            if isinstance(people, str):
                people = [people]
            if not isinstance(people, list):
                continue

            # Check if any person link resolves to our target person file
            found = False
            for person_link in people:
                if not isinstance(person_link, str):
                    continue

                # Extract the file path from wikilink
                if '[[' in person_link:
                    # Format: [[path/to/person.md|Display]] or [[path/to/person.md]]
                    path_part = person_link.split('[[')[1].split('|')[0].split(']]')[0]
                    # Resolve relative to note's directory
                    note_dir = os.path.dirname(file_path)
                    # not a relative path
                    if path_part.startswith('people'):
                        # remove one `people/` from the path since its shared across both
                        resolved = os.path.join(os.path.dirname(people_path), path_part)
                    # likely starts with `../..`
                    else:
                        resolved = os.path.normpath(os.path.join(note_dir, path_part))

                    if os.path.exists(resolved) and os.path.samefile(resolved, person_file):
                        found = True
                        break

            if found:
                # Group by specified period
                if group_by == 'year':
                    key = f"{date.year}"
                elif group_by == 'quarter':
                    quarter = (date.month - 1) // 3 + 1
                    key = f"{date.year}-Q{quarter}"
                else:  # month
                    key = f"{date.year}-{date.month:02d}"

                timeline[key] += 1
        # except Exception as e:
        #     print(f'Something happened: {e}')
        #     break
        # continue

    return dict(sorted(timeline.items(), reverse=True)), display_name, all_aliases


def render_timeline_chart(timeline: dict, person_name: str, all_aliases: list, max_width: int = 60) -> None:
    """Render a text-based timeline chart.

    Args:
        timeline: Dictionary with time periods as keys and counts as values (reverse sorted)
        person_name: Display name of person
        all_aliases: List of all aliases for this person
        max_width: Maximum width of bars in characters
    """
    if not timeline:
        click.echo(f"\nNo mentions found for '{person_name}'")
        return

    max_count = max(timeline.values())
    total_mentions = sum(timeline.values())

    click.echo(f"\n📈 Timeline for {person_name}")
    if all_aliases and len(all_aliases) > 1:
        alias_str = ", ".join(f"'{a}'" for a in all_aliases if a != person_name)
        click.echo(f"   (also known as: {alias_str})")
    click.echo(f"   Total mentions: {total_mentions} across {len(timeline)} periods\n")

    # Calculate scale
    scale = max_width / max_count if max_count > 0 else 1

    # Find longest period label for alignment
    max_label_len = max(len(str(period)) for period in timeline.keys())

    # Render bars (already reverse sorted, so newest first)
    for period, count in timeline.items():
        bar_length = int(count * scale)
        bar = '█' * bar_length
        percentage = (count / total_mentions * 100) if total_mentions > 0 else 0

        # Format: "2023-01 ████████ 15 (10.5%)"
        label = str(period).ljust(max_label_len)
        click.echo(f"   {label} {bar} {count} ({percentage:.1f}%)")


@click.command()
@click.option('--detailed', '-d', is_flag=True, help='Show detailed statistics')
def stats(detailed):
    """Show vault statistics."""
    config = get_config()

    click.echo("📊 Vault Statistics\n")
    click.echo(f"Vault: {config.vault_path}\n")

    # Count notes by category
    pensieve_count = count_notes(config.pensieve_path)
    people_count = count_notes(config.people_path)
    locations_count = count_notes(config.locations_path)

    click.echo(f"📝 Notes:")
    click.echo(f"  Daily notes: {pensieve_count}")
    click.echo(f"  People: {people_count}")
    click.echo(f"  Locations: {locations_count}")

    # Photo coverage
    if config.photos_path.exists():
        photo_stats = get_photo_coverage(config.pensieve_path, config.photos_path)
        click.echo(f"\n📷 Photo Coverage:")
        click.echo(f"  Notes with photos: {photo_stats['notes_with_photos']}/{photo_stats['total_notes']}")
        click.echo(f"  Coverage: {photo_stats['coverage_pct']:.1f}%")

    # People frequency
    if detailed:
        click.echo("\n👥 Top People (by mention frequency):")
        people_freq = get_people_frequency(config.pensieve_path)
        for person, count in sorted(people_freq.items(), key=lambda x: x[1], reverse=True)[:10]:
            click.echo(f"  {person}: {count}")

        click.echo("\n📍 Top Locations:")
        location_freq = get_locations_frequency(config.pensieve_path)
        for loc, count in sorted(location_freq.items(), key=lambda x: x[1], reverse=True)[:10]:
            click.echo(f"  {loc}: {count}")


@click.command()
@click.argument('person_name')
@click.option('--group-by', type=click.Choice(['year', 'month', 'quarter']), default='month',
              help='How to group timeline data')
@click.option('--width', default=100, help='Maximum width of chart bars')
def person_timeline(person_name, group_by, width):
    """Show timeline chart for a specific person (matches any alias)."""
    config = get_config()

    try:
        timeline, display_name, all_aliases = get_person_timeline(
            config.pensieve_path,
            config.people_path,
            person_name,
            group_by
        )

        if display_name is None:
            click.echo(f"\n❌ No person found matching '{person_name}'", err=True)
            click.echo(f"   Run 'pkms stats --detailed' to see available people", err=True)
            return

        render_timeline_chart(timeline, display_name, all_aliases, max_width=width)
    except ValueError as e:
        # Duplicate alias error already printed
        return
