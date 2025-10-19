import click
import glob
from pkms.core.config import get_config

@click.command('combine')
@click.option('--year', required=True, help='Year to combine')
def combine(year):
    """Combine all notes for a given year into a single file."""
    config = get_config()
    existing_files = glob.glob(f'{config.pensieve_path}/{year}/*/*')
    year_file = f'{config.vault_path}/{year}.txt'

    with open(year_file, 'w') as w:
        for file_path in existing_files:
            with open(file_path, 'r') as r:
                text = r.read()
                if not text:
                    continue
            w.write(text + '\n\n')
    click.echo(f"Combined {len(existing_files)} files into {year_file}")
