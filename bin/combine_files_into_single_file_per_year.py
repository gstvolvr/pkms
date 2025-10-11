from typing import Optional
import glob
import re
import requests
import util


def main():

    years = ['2018', '2019', '2020', '2021', '2022', '2023']

    for year in years:
        existing_files = glob.glob(f'{util.PENSIEVE_PATH}/{year}/*/*')
        year_file = f'/Users/Home/My Drive/pensieve/{year}.txt'

        with open(year_file, 'w') as w:
            for file_path in existing_files:
                with open(file_path, 'r') as r:
                    text = r.read()
                    if not text:
                        continue

                # add any processing you want to the text here

                w.write(text + '\n\n')


if __name__ == '__main__':
    main()
