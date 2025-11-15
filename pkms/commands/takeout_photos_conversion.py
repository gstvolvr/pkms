import os
import json
import click
from PIL import Image
import piexif
from datetime import datetime

def _convert_to_rational(value):
    deg = int(value)
    min_ = int((value - deg) * 60)
    sec = int((value - deg - min_ / 60) * 3600 * 10000)
    return ((deg, 1), (min_, 1), (sec, 10000))

def update_metadata(photo_path, json_path):
    """
    Update JPG file with metadata from JSON.
    """
    with open(json_path, 'r') as f:
        metadata = json.load(f)

    creation_time = metadata.get('photoTakenTime', {}).get('timestamp')
    caption = metadata.get('description', "")

    lat, lon = None, None
    gps_data = metadata.get('geoData', {})
    if gps_data:
        lat = gps_data.get('latitude')
        lon = gps_data.get('longitude')

    if creation_time:
        creation_date = datetime.utcfromtimestamp(int(creation_time)).strftime('%Y:%m:%d %H:%M:%S')
    else:
        creation_date = None

    try:
        exif_dict = piexif.load(photo_path)
        if creation_date:
            exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = creation_date
            exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = creation_date

        if lat and lon:
            gps_ifd = {
                piexif.GPSIFD.GPSLatitude: _convert_to_rational(lat),
                piexif.GPSIFD.GPSLatitudeRef: 'N' if lat >= 0 else 'S',
                piexif.GPSIFD.GPSLongitude: _convert_to_rational(lon),
                piexif.GPSIFD.GPSLongitudeRef: 'E' if lon >= 0 else 'W',
            }
            exif_dict['GPS'] = gps_ifd

        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, photo_path)

        click.echo(f"Metadata updated for {photo_path}")
    except Exception as e:
        click.echo(f"Failed to update metadata for {photo_path}: {str(e)}", err=True)

@click.command('takeout-convert')
@click.option('--photo-dir', required=True, help='Directory of the Google Takeout photos')
def takeout_convert(photo_dir):
    """Process all photos in the given directory."""
    for file_name in os.listdir(photo_dir):
        if file_name.endswith('.jpg'):
            photo_path = os.path.join(photo_dir, file_name)
            json_path = os.path.join(photo_dir, file_name + '.json')
            if os.path.exists(json_path):
                update_metadata(photo_path, json_path)
