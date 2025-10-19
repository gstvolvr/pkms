import os
import glob
import calendar
import click
from pkms.core.config import get_config

@click.command('rename')
@click.option('--year', required=True, type=int, help='Year to rename files for')
def rename(year):
    """Rename pensieve files for a given year."""
    config = get_config()
    notes_path = config.pensieve_path

    for month in range(1, 13):
        month_path = os.path.join(notes_path, str(year), str(month).rjust(2, '0'))
        if not os.path.exists(month_path):
            continue

        _, days_in_month = calendar.monthrange(year, month)

        for day in range(1, days_in_month + 1):
            date_path = os.path.join(month_path, f'{year}{str(month).rjust(2, "0")}{str(day).rjust(2, "0")}.md')
            new_name = os.path.join(month_path, f'{str(year)[-2:]}{str(month).rjust(2, "0")}{str(day).rjust(2, "0")}.md')

            if os.path.exists(date_path):
                os.rename(date_path, new_name)
    click.echo(f"Renamed files for {year}")
