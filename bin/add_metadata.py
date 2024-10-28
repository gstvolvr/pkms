import frontmatter
import glob
import util
import re


def init_meta(path: str) -> None:
    with open(path, 'r') as f:
        text = f.read()
        if 'people:' in text and 'locations:' in text:
            print(f'metadata exists for: {path}\n\nskipping...')
            return

    post = frontmatter.load(path)
    post['people'] = []
    post['locations'] = []
    post['date'] = util.get_date_from_path(path)

    frontmatter.dump(post, path)

def md_path_to_yaml_path(md_path: str) -> str:
    """Convert markdown path to yaml path

    input: '[First Last](../../../../people/family/First%20Last.md)'
    output: [[../../../../people/family/First Last|First List]]
    """
    return f'[[{get_md_path_value(md_path).replace("%20", " ")}|{get_md_path_key(md_path).replace("%20", " ")}]]'

def get_md_path_value(md_path: str) -> str:
    return md_path.split('(')[1].replace(')', '')

def get_md_path_key(md_path: str) -> str:
    name = md_path.split('/')[-1]
    return name.replace('%20', ' ').replace('.md', '').replace(')', '')


def get_yaml_path_key(yaml_path: str) -> str:
    name = yaml_path.split('/')[-1]
    return name.split('|')[0].replace('.md', '')


def enrich_meta(path: str) -> None:
    """Capture links from the text and add them to the metadata"""

    post = frontmatter.load(path)
    if post['people'] is None:
        return
    people_pattern = re.compile("""
        (
        \[
            [a-zA-Z\-|\s]+
        \]
        \(

            [\./]+
            people
            [\.a-zA-Z\s\-/0-9%]+
        \)
        )
    """, re.VERBOSE | re.IGNORECASE)

    with open(path, 'r') as f:
        text = f.read()
        people_md = re.findall(people_pattern, text)
        md_path = {get_md_path_key(p): p for p in people_md}
        yaml_path = {get_yaml_path_key(p): p for p in post['people']}

        md_keys = set(md_path.keys())
        yaml_keys = set(yaml_path.keys())
        missing_keys = md_keys - yaml_keys

        if len(missing_keys) > 0:
            print(path)
            print(f'misisng keys: {missing_keys}')
            for k in missing_keys:
                this_yaml_path = md_path_to_yaml_path(md_path[k])
                if this_yaml_path not in post['people']:
                    post['people'].append(this_yaml_path)
        post['people'] = list(set(post['people']))

    frontmatter.dump(post, path)



if __name__ == '__main__':
    existing_files = glob.glob(f'{util.PENSIEVE_PATH}/*/*/*')

    for i, path in enumerate(existing_files):
        #init_meta(path)
        enrich_meta(path)
