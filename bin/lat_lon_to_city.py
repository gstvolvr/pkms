from sitecustomize import long_prefix

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut


if __name__ == "__main__":
    # Example latitude and longitude
    latitude = 42.32586333333333
    longitude = -71.1492695

    city, state = get_city_state(latitude, longitude)
    if city and state:
        print(f"The location is in {city}, {state}.")
    else:
        print("Unable to determine the location.")
