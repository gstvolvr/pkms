import os
import glob


MONTHS = range(1, 13)
base_path = '/Users/Home/Library/Mobile Documents/iCloud~md~obsidian/Documents/life'
notes_path = os.path.join(base_path, 'pensieve')

existing_files = glob.glob(f'{notes_path}/*/*/*/*')

# remove empty files
for path in existing_files:
    with open(path, 'r') as f:
        lines = f.readlines()

    # if we only have the incorrectly set template then remove the file
    if len(lines) == 2:
        os.remove(path)



years = os.listdir(f'{notes_path}/day')

# remove empty `month` directories
for year in years:
    if '.' in year:
        continue
    months = os.listdir(f'{notes_path}/day/{year}')
    for month in months:
        if '.' in month:
            continue
        days = os.listdir(f'{notes_path}/day/{year}/{month}')
        if not days:
            os.rename(f'{notes_path}/day/{year}/{month}', f'{base_path}/.trash/{month}')
