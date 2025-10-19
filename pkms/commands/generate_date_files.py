import os
import calendar
import datetime
import click
from pkms.core.config import get_config

@click.command('generate-dates')
@click.option('--year', required=True, type=int, help='Year to generate date files for')
def generate_dates(year):
    """Generate date files for a given year."""
    config = get_config()
    notes_path = config.pensieve_path
    
    for month in range(1, 13):
        month_path = os.path.join(notes_path, str(year), str(month).rjust(2, '0'))
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
    click.echo(f"Generated date files for {year}")
