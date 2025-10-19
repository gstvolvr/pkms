import click
from pkms.core.utils import get_city_state

@click.group('location')
def location():
    """Commands for location-based services."""
    pass

@location.command('reverse-geocode')
@click.option('--lat', required=True, type=float, help='Latitude')
@click.option('--lon', required=True, type=float, help='Longitude')
def reverse_geocode(lat, lon):
    """Get city and state from latitude and longitude."""
    city, state = get_city_state(lat, lon)
    if city and state:
        click.echo(f"The location is in {city}, {state}.")
    else:
        click.echo("Unable to determine the location.")
