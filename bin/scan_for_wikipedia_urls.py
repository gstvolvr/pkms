from typing import Optional
import glob
import re
import requests
import util


WIKI_API = 'https://en.wikipedia.org/w/api.php'
TOKEN_PATTERN = r'{{([A-Za-z0-9,: ()]+)}}'


def _find_all_files(path: str):
    files = []

    files.extend(glob.glob(f'{path}/*.md'))
    files.extend(glob.glob(f'{path}/*/*.md'))
    files.extend(glob.glob(f'{path}/*/*/*.md'))
    files.extend(glob.glob(f'{path}/*/*/*/*.md'))

    return files

def main(existing_files: list):
    for file_path in existing_files:
        print(file_path)
        with open(file_path, 'r') as r:
            text = r.read()
            if not text:
                continue

            hyperlinked_text = find_and_replace_tokens_with_url(text)

            if not hyperlinked_text:
                continue

        with open(file_path, 'w') as w:
            w.write(hyperlinked_text)

def pensieve():
    existing_files = glob.glob(f'{util.PENSIEVE_PATH}/*/*/*')
    main(existing_files)


def summaries():
    existing_files = _find_all_files(util.SUMMARIES_PATH)
    main(existing_files)


def concepts():
    existing_files = _find_all_files(util.CONCEPTS_PATH)
    #print(existing_files)
    main(existing_files)



def find_and_replace_tokens_with_url(text: str) -> Optional[str]:
    tokens = re.findall(TOKEN_PATTERN, text)
    if not tokens:
        return

    for token in tokens:
        url = generate_wikipedia_url(token)
        #print(token, url)
        if url:
            text = text.replace('{{' + token + '}}', f'[{token}]({url})')
    return text


def generate_wikipedia_url(token: str) -> Optional[str]:
    params = {
        'action': 'query',
        'format': 'json',
        'prop': 'info',
        'generator': 'allpages',
        'list': 'search',
        'inprop': 'url',
        'gapfrom': token,
        'srsearch': token,
    }

    response = requests.get(WIKI_API, params=params)

    if response.status_code == 200:
        content = response.json()
        if content['query']['search']:
            page_id = content['query']['search'][0]['pageid']
            print(token, page_id)
            print(content['query']['search'])
            print(content['query']['pages'].keys())
            print(content['query']['pages'])
            page_metadata = content['query']['pages'].get(str(page_id), {})
            if not page_metadata:
                # TODO: WIP
                # try and query based on pageid
                requests.get(WIKI_API, params={
                    'action': 'query',
                    'format': 'json',
                    'prop': 'info',
                    'generator': 'allpages',
                    'list': 'search',
                    'inprop': 'url',
                })
                pass
            print(page_metadata)
            return page_metadata.get('canonicalurl')


if __name__ == '__main__':
    #pensieve()
    summaries()
    #concepts()

