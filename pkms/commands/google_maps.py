import os
import click
import googlemaps
from markdownify import markdownify

@click.group('maps')
def maps():
    """Commands for interacting with Google Maps."""
    pass

@maps.command('import')
@click.option('--api-key', required=True, help='Google Maps API key')
@click.option('--place-id', required=True, multiple=True, help='Google Maps Place ID to import')
def maps_import(api_key, place_id):
    """Import Google Maps place details."""
    gmaps = googlemaps.Client(key=api_key)
    output_dir = "obsidian"
    os.makedirs(output_dir, exist_ok=True)

    for pid in place_id:
        try:
            place = gmaps.place(place_id=pid)
            result = place.get("result", {})
            place_details = {
                "name": result.get("name"),
                "address": result.get("formatted_address"),
                "phone": result.get("formatted_phone_number"),
                "website": result.get("website"),
                "rating": result.get("rating"),
                "reviews": result.get("user_ratings_total"),
                "notes": markdownify(result.get("editorial_summary", {}).get("overview", ""))
            }
            filename = f"{place_details['name'].replace(' ', '_').replace('/', '-')}.md"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w", encoding="utf-8") as file:
                file.write(f"# {place_details['name']}\n\n")
                file.write(f"**Address**: {place_details['address']}\n\n")
                if place_details['phone']:
                    file.write(f"**Phone**: {place_details['phone']}\n\n")
                if place_details['website']:
                    file.write(f"**Website**: [Link]({place_details['website']})\n\n")
                if place_details['rating']:
                    file.write(f"**Rating**: {place_details['rating']} ({place_details['reviews']} reviews)\n\n")
                if place_details['notes']:
                    file.write(f"**Notes**:\n\n{place_details['notes']}\n\n")
            click.echo(f"Markdown file created: {filepath}")
        except Exception as e:
            click.echo(f"Error fetching details for Place ID {pid}: {e}")
