import os
from collections import defaultdict
import click

@click.command('takeout-cleanup')
@click.option('--takeout-dir', required=True, help='Directory of the Google Photos Takeout')
@click.option('--output-dir', required=True, help='Directory to save the cleaned photos')
def takeout_cleanup(takeout_dir, output_dir):
    """Clean up Google Photos Takeout files, keeping only photos with sidecars."""
    d = defaultdict(list)
    filenames = os.listdir(takeout_dir)

    for filename in filenames:
        base = filename.split('.')[0]
        d[base].append(filename)

    for filename, files in d.items():
        if len(files) == 2:
            for file in files:
                with open(os.path.join(takeout_dir, file), 'rb') as f_src:
                    file = file.lower().replace(' ', '_')
                    if file.endswith('.json'):
                        file = '.'.join(file.split('.')[:-2]) + '.json'
                    with open(os.path.join(output_dir, file), 'wb') as f_dest:
                        f_dest.write(f_src.read())
    click.echo("Takeout cleanup complete.")
