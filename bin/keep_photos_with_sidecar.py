import os
from collections import defaultdict

if __name__ == '__main__':

    d = defaultdict(list)
    dir = '/Users/Home/photos/Takeout-2/Google Photos/Gustavo Antonio Oliver Andraca'
    out_dir = '/Users/Home/photos/Takeout/Google Photos/'
    filenames = os.listdir(dir)

    for filename in filenames:
        base = filename.split('.')[0]
        d[base].append(filename)

    for filename, files in d.items():
        if len(files) == 2:
            for file in files:
                with open(os.path.join(dir, file), 'rb') as f_src:
                    file = file.lower().replace(' ', '_')
                    if file.endswith('.json'):
                        file = '.'.join(file.split('.')[:-2]) + '.json'
                    with open(os.path.join(out_dir, file), 'wb') as f_dest:
                        f_dest.write(f_src.read())
