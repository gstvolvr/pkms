from typing import List
import glob
import os
import util
import random

"""
Add photos paths to markdown files
"""


PHOTO_DATE_DIR = f"{util.PHOTOS_PATH}/{{year}}/{{month}}/{{date}}"


def get_photos(path: str) -> List[str]:
    """
    path follows the pattern like: ${USER}/{VAULT}/pensieve/day/2018/12/181212.md
    """
    year, month, file_name = path.split('/')[-3:]
    date = file_name.split('.')[0][-2:]

    for root, dirs, files in os.walk(PHOTO_DATE_DIR.format(year=year, month=month, date=date)):
        for file in files:
            if file.lower().endswith('jpeg') or file.lower().endswith('jpg'):
                # TODO: use user directory
                yield '/'.join(['/Users', 'home', 'photos', year, month, date, file])


def markdown_grid(paths: List[str]) -> str:
    image_tags = '\n'.join([f'<img src="file://{p}" width="100"/>' for p in paths])
    return f"""<p align="center">
{image_tags}
</p>
    """

def markdown_photo(path: str) -> str:
    return f"![200](file://{path})\n"


def main():
    existing_files = glob.glob(f'{util.PENSIEVE_PATH}/*/*/*')
    for i, path in enumerate(existing_files):
        paths = list(get_photos(path))
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
            w.write('\n')
            w.write(grid)


if __name__ == '__main__':
    main()
