import os
import glob
import calendar
import datetime


MONTHS = range(1, 13)
base_path = '/Users/Home/Library/Mobile Documents/iCloud~md~obsidian/Documents/life'
notes_path = os.path.join(base_path, 'pensieve/day')

existing_files = glob.glob(f'{notes_path}/*/*/*')

years = [2022]

for year in years:
    year_path = os.path.join(notes_path, str(year))
    os.makedirs(year_path, exist_ok=True)
    for month in MONTHS:
        month_path = os.path.join(year_path, str(month).rjust(2, '0'))

        os.makedirs(month_path, exist_ok=True)

        _, days_in_month = calendar.monthrange(year, month)

        for day in range(1, days_in_month + 1):

            file_name = str(year) + '_' + str(month).rjust(2, '0') + '_' + str(day).rjust(2, "0")
            date_path = f'{os.path.join(month_path, file_name)}.md'

            if os.path.exists(date_path):
                continue

            date = datetime.date(year, month, day)
            if date > datetime.date.today():
                date_title = date.strftime('%A, %B %d')
                with open(date_path, 'w') as f:
                    f.write(f'# {date_title}\n')
                    f.write('---\n')

# for year in years:
#     for month in
# calendar.monthrange(2020, 2))

# for year in os.listdir(notes_path):
#     print(year)
#     print(os.listdir(os.path.join(notes_path, year)))
#
