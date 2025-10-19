import click
from pkms.core.utils import find_all_files
from pkms.core.config import get_config

@click.command('year-tag')
def year_tag():
    """Add year tag to all notes."""
    config = get_config()
    files = find_all_files(str(config.pensieve_path))
    for file_path in files:
        click.echo(f"Processing {file_path}")
        year = file_path.split('/')[-3]
        with open(file_path, 'r') as rf:
            text = rf.read()
        with open(file_path, 'w') as wf:
            wf.write(f'{text}\n\n#{year}')
