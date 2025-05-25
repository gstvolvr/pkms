from typing import List
import glob
import os
import util
import random

"""
Add photos paths to markdown files
"""


PHOTO_DATE_DIR = f"{util.PHOTOS_PATH}/{{year}}/{{month}}/{{date}}"


def get_photo_files(path: str, postfixes: List[str] = ['jpeg', 'jpg']) -> List[str]:
    """
    path follows the pattern like: ${USER}/{VAULT}/pensieve/day/2018/12/181212.md
    """
    year, month, file_name = path.split('/')[-3:]
    date = file_name.split('.')[0][-2:]

    for root, dirs, files in os.walk(PHOTO_DATE_DIR.format(year=year, month=month, date=date)):
        for file in files:
            if file.lower().split('.')[-1] in postfixes:
                # TODO: use user directory
                yield '/'.join(['/Users', 'home', 'photos', year, month, date, file])


def markdown_grid(paths: List[str]) -> str:
    image_tags = '\n'.join([f'<img src="file://{p}" width="300"/>' for p in paths])
    return f"""<p align="center">
{image_tags}
</p>
    """

def markdown_photo(path: str) -> str:
    return f"![400](file://{path})\n"


def main():
    existing_files = glob.glob(f'{util.PENSIEVE_PATH}/*/*/*')
    n_updates = 0
    for i, path in enumerate(existing_files):
        paths = list(get_photo_files(path))
        random.shuffle(paths)

        if len(paths) == 0:
            continue

        grid = markdown_grid([photo_path for j, photo_path in enumerate(paths) if j < 4])
        with open(path, 'r') as r:
            if '<p align' in r.read():
               print(f'skipping: {path}')
               continue

        with open(path, 'a') as w:
            print(f'appending: {path}')
            n_updates += 1
            w.write('\n')
            w.write(grid)
    print(f'Updated {n_updates} files.')


if __name__ == '__main__':
    main()
