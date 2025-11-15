from typing import Optional
import glob
import re
import requests
import click
from pkms.core.config import get_config
from pkms.core.utils import find_all_files

WIKI_API = 'https://en.wikipedia.org/w/api.php'
TOKEN_PATTERN = r'{{([A-Za-z0-9,: ()]+)}}'

def find_and_replace_tokens_with_url(text: str) -> Optional[str]:
    tokens = re.findall(TOKEN_PATTERN, text)
    if not tokens:
        return

    for token in tokens:
        url = generate_wikipedia_url(token)
        if url:
            text = text.replace('{{' + token + '}}', f'[{token}]({url})')
    return text

def generate_wikipedia_url(token: str) -> Optional[str]:
    params = {
        'action': 'query',
        'format': 'json',
        'list': 'search',
        'srsearch': token,
    }

    response = requests.get(WIKI_API, params=params)

    if response.status_code == 200:
        content = response.json()
        if content['query']['search']:
            page_id = content['query']['search'][0]['pageid']
            return f"https://en.wikipedia.org/?curid={page_id}"

@click.command('scan-wikipedia')
@click.option('--path', default='pensieve', help='Path to scan (pensieve, summaries, or concepts)')
def scan_wikipedia(path):
    """Scan for tokens and replace them with Wikipedia URLs."""
    config = get_config()
    if path == 'pensieve':
        scan_path = str(config.pensieve_path)
    elif path == 'summaries':
        scan_path = str(config.summaries_path)
    elif path == 'concepts':
        scan_path = str(config.concepts_path)
    else:
        click.echo("Invalid path specified. Please choose from 'pensieve', 'summaries', or 'concepts'.", err=True)
        return

    existing_files = find_all_files(scan_path)
    for file_path in existing_files:
        with open(file_path, 'r') as r:
            text = r.read()
            if not text:
                continue

            hyperlinked_text = find_and_replace_tokens_with_url(text)

            if not hyperlinked_text:
                continue

        with open(file_path, 'w') as w:
            w.write(hyperlinked_text)
    click.echo(f"Scanned {len(existing_files)} files.")
