"""Main CLI entry point for PKMS."""
import click
import sys
from pathlib import Path

from pkms.core import Config, set_config
from pkms.commands.search import search
from pkms.commands.defaults import defaults
from pkms.analytics.stats import stats, person_timeline
from pkms.commands.viz import viz
from pkms.commands.year_tag import year_tag
from pkms.commands.combine import combine
from pkms.commands.generate_date_files import generate_dates as generate_dates_cmd
from pkms.commands.get_photos import export as export_cmd
from pkms.commands.google_maps import maps
from pkms.commands.takeout import takeout_cleanup
from pkms.commands.location import location
from pkms.commands.llm import llm
from pkms.commands.rag import rag
from pkms.commands.process_metadata import process as process_metadata_cmd
from pkms.commands.wipe_bad_metadata import wipe as wipe_cmd
from pkms.commands.rename_pensive_files import rename as rename_cmd
from pkms.commands.scan_for_people import scan_people
from pkms.commands.scan_for_wikipedia_urls import scan_wikipedia


@click.group()
@click.option('--vault', type=click.Path(exists=True), help='Path to Obsidian vault')
@click.option('--photos', type=click.Path(exists=True), help='Path to photos directory')
@click.version_option()
def cli(vault, photos):
    """Personal Knowledge Management System - CLI for Obsidian vault management."""
    # Set up configuration
    config = Config(vault_path=vault, photos_path=photos)
    try:
        config.validate()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    set_config(config)


# Add command groups
cli.add_command(search)
cli.add_command(stats)
cli.add_command(defaults)
cli.add_command(viz)
cli.add_command(year_tag)
cli.add_command(combine)
cli.add_command(maps)
cli.add_command(location)
cli.add_command(llm)
cli.add_command(rag)


@cli.group()
def metadata():
    """Manage note metadata (people, locations, dates)."""
    pass


@metadata.command('init')
@click.option('--dry-run', is_flag=True, help='Preview changes without applying')
def metadata_init(dry_run):
    """Initialize frontmatter for notes."""
    from pkms.commands.metadata import init_meta
    from pkms.core import get_config, find_all_files

    config = get_config()
    files = find_all_files(str(config.pensieve_path))

    click.echo(f"Initializing metadata for {len(files)} files...")
    count = 0

    for path in files:
        try:
            if not dry_run:
                init_meta(path)
            count += 1
        except Exception as e:
            click.echo(f"Error processing {path}: {e}", err=True)

    if dry_run:
        click.echo(f"Would initialize {count} files (dry run)")
    else:
        click.echo(f"✓ Initialized {count} files")


@metadata.command('enrich')
@click.option('--auto-approve', '-a', is_flag=True, help='Auto-approve from approved list')
@click.option('--approved-file', default='auto_approved_people.txt', help='File with auto-approved names')
def metadata_enrich(auto_approve, approved_file):
    """Enrich metadata from photo data."""
    from pkms.commands.metadata import auto_add_people_from_photos, prompt_add_people_from_photos

    if auto_approve:
        click.echo(f"Auto-approving people from {approved_file}...")
        auto_add_people_from_photos(approved_names_source=approved_file)
    else:
        click.echo("Starting interactive review...")
        prompt_add_people_from_photos()


@metadata.command('count')
def metadata_count():
    """Count pending metadata items."""
    from pkms.commands.metadata import count_candidate_people

    remaining = count_candidate_people()
    click.echo(f"Pending metadata candidates: {remaining}")


@metadata.command('review')
@click.option('--interactive', '-i', is_flag=True, help='Interactive review mode')
@click.option('--auto', '-a', is_flag=True, help='Auto-apply standardization')
def metadata_review(interactive, auto):
    """Review and standardize metadata."""
    from pkms.commands.review_metadata import run_interactive, run_auto

    if interactive:
        run_interactive()
    else:
        run_auto()


metadata.add_command(process_metadata_cmd)
metadata.add_command(wipe_cmd)


@metadata.command('outliers')
@click.option('--interactive', '-i', is_flag=True, help='Interactive outlier review')
@click.option('--count', '-c', is_flag=True, help='Count outliers')
@click.option('--min-appearances', default=10, help='Minimum appearances threshold')
def metadata_outliers(interactive, count, min_appearances):
    """Find and review outlier people in notes."""
    from pkms.commands.review_metadata import review_outliers_interactive, _count_remaining_outliers, find_outlier_people

    if count:
        remaining = _count_remaining_outliers(min_appearances=min_appearances)
        click.echo(f"Pending outlier suggestions: {remaining}")
    elif interactive:
        review_outliers_interactive(min_appearances=min_appearances)
    else:
        find_outlier_people(min_appearances=min_appearances)


@cli.group()
def links():
    """Manage entity links in notes."""
    pass


@links.command('add')
@click.option('--interactive', '-i', is_flag=True, default=True, help='Interactive mode')
def links_add(interactive):
    """Add entity links interactively."""
    from pkms.commands.add_links import main

    if interactive:
        main()


links.add_command(scan_people)
links.add_command(scan_wikipedia)


@links.command('count')
def links_count():
    """Count pending link candidates."""
    from pkms.commands.add_links import count_candidate_links

    remaining = count_candidate_links()
    click.echo(f"Pending link candidates: {remaining}")


@cli.group()
def photos():
    """Manage photos in notes."""
    pass


photos.add_command(export_cmd)
photos.add_command(takeout_cleanup)


@photos.command('add')
@click.option('--max-photos', default=4, help='Maximum photos per note')
def photos_add(max_photos):
    """Add photo grids to notes."""
    from pkms.commands.add_photos import main

    main()





@photos.command('sync')
@click.option('--create-notes', is_flag=True, help='Create notes based on photos')
def photos_sync(create_notes):
    """Sync photo metadata to notes."""
    from pkms.commands.add_metadata import load_photo_metadata_into_md_frontmatter, create_notes_based_on_photos

    if create_notes:
        click.echo("Creating notes from photo metadata...")
        create_notes_based_on_photos()

    click.echo("Loading photo metadata into frontmatter...")
    load_photo_metadata_into_md_frontmatter()
    click.echo("✓ Photo metadata synced")


@cli.group()
def files():
    """Manage vault files."""
    pass


files.add_command(generate_dates_cmd)
files.add_command(rename_cmd)


@files.command('generate-dates-from-photos')
def generate_dates():
    """Generate date files from photos."""
    from pkms.commands.add_metadata import create_notes_based_on_photos

    create_notes_based_on_photos()
    click.echo("✓ Date files generated")





if __name__ == '__main__':
    cli()
