from typing import Optional, List, Dict, Any
import glob
import re
import os
import collections
import click
from pkms.core.config import get_config
from pkms.core.utils import find_all_files

NICKNAMES = {
    ('Alicia', 'Andraca'): ['mama', 'mom'],
    ('Roberto', 'Oliver'): ['dad', 'papa'],
    ('Javier', 'Ramos'): ['javi'],
    ('Monica', 'Oliver'): ['moni'],
    ('Courtney', 'Oliver'): ['c']
}

def find_all_people() -> dict[Any, Any]:
    config = get_config()
    people_files = []
    # don't care about 'authors' etc
    for subdir in ['family', 'friends', 'co-workers', 'pets']:
        people_files.extend(find_all_files(f'{config.people_path}/{subdir}'))
    names_to_file = {tuple(file_name.split('/')[-1].replace('.md', '').split(' ')): file_name for file_name in people_files}
    first_name_to_file = {}
    d = collections.defaultdict(int)
    for name in names_to_file:
        fn = name[0]
        d[fn] += 1

    for name, path in names_to_file.items():
        fn = name[0]
        if (d[fn] == 1) and fn not in ('Juan', 'Jim', 'Tim', 'Ali', 'Alex', 'Will'):
            first_name_to_file[fn] = path

        for nickname in NICKNAMES.get(name, []):
            first_name_to_file[nickname] = path

    return first_name_to_file

def find_and_replace_name_with_link(text: str, file_path: str, names_to_path: dict):
    for name, path in names_to_path.items():
        pattern = re.compile(r'\b' + name + r'\b', re.IGNORECASE)
        path = os.path.relpath(path, start=os.path.dirname(file_path)).replace(' ', '%20')
        if name.lower() in text.lower() and re.findall(pattern, text):
            new_text = re.sub(pattern, f'[{name.title()}]({path})', text)
            return new_text
    return None

@click.command('scan-people')
def scan_people():
    """Scan for people's names and create links."""
    config = get_config()
    existing_files = find_all_files(str(config.pensieve_path))
    names_to_path = find_all_people()
    n_files = 0
    for file_path in existing_files:
        with open(file_path, 'r') as r:
            text = r.read()
            if not text:
                continue

            hyperlinked_text = find_and_replace_name_with_link(text, file_path, names_to_path)

            if not hyperlinked_text:
                continue

            n_files += 1

            with open(file_path, 'w') as w:
                w.write(hyperlinked_text)
    click.echo(f'Number of files updated: {n_files}')
