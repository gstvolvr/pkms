import util
import glob

existing_files = glob.glob(f'{util.PENSIEVE_PATH}/*/*/*')

for file_path in existing_files[:1]:
    print(file_path)
    year = file_path.split('/')[-3]
    with open(file_path, 'r') as rf:
        text = rf.read()
        print(f'{text}\n\n#{year}')
        with open(file_path.replace('.md', '_edit.md'), 'w') as wf:
            wf.write(f'{text}\n\n#{year}')

