import os.path
import click
import osxphotos

@click.command('export')
@click.option('--export-path', default='~/Documents/export', help='Path to export photos to')
def export(export_path):
    """Export photos from Photos library."""
    db = os.path.expanduser("~/Pictures/Photos Library.photoslibrary")
    photosdb = osxphotos.PhotosDB(db)
    photos = photosdb.photos()

    export_path = os.path.expanduser(export_path)

    for p in photos:
        if not p.ismissing:
            if p.hasadjustments:
                exported = p.export(export_path, edited=True)
            else:
                exported = p.export(export_path)
            click.echo(f"Exported {p.filename} to {exported}")
        else:
            click.echo(f"Skipping missing photo: {p.filename}")
