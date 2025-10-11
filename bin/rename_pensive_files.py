import os
import glob
import calendar


MONTHS = range(1, 13)
base_path = '/Users/Home/Library/Mobile Documents/iCloud~md~obsidian/Documents/life'
notes_path = os.path.join(base_path, 'pensieve', 'day')
existing_files = glob.glob(f'{notes_path}/*/*/*')

years = [2022, 2021, 2020, 2019, 2018]

for year in years:
    year_path = os.path.join(notes_path, str(year))
    os.makedirs(year_path, exist_ok=True)
    for month in MONTHS:
        month_path = os.path.join(year_path, str(month).rjust(2, '0'))

        os.makedirs(month_path, exist_ok=True)

        _, days_in_month = calendar.monthrange(year, month)

        for day in range(1, days_in_month + 1):

            date_path = f'{os.path.join(month_path, str(day).rjust(2, "0"))}.md'

            date_path = os.path.join(month_path, f'{year}{str(month).rjust(2, "0")}{str(day).rjust(2, "0")}.md')
            new_name = os.path.join(month_path, f'{str(year)[-2:]}{str(month).rjust(2, "0")}{str(day).rjust(2, "0")}.md')

            if os.path.exists(date_path):
                os.rename(date_path, new_name)
                #print(date_path, new_name)
                #continue

            # with open(date_path, 'w') as f:
            #     f.write(f'# {date_title}\n')
            #     f.write('---\n')

# for year in years:
#     for month in
# calendar.monthrange(2020, 2))

# for year in os.listdir(notes_path):
#     print(year)
#     print(os.listdir(os.path.join(notes_path, year)))
#
