import os
import googlemaps
from markdownify import markdownify

# Set up your Google Maps API key
API_KEY = "YOUR_GOOGLE_MAPS_API_KEY"
gmaps = googlemaps.Client(key=API_KEY)

# Directory for storing markdown notes
OUTPUT_DIR = "obsidian"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Example saved places (replace with your list of place IDs)
saved_places = [
    "ChIJCzYy5IS16lQRQrfeQ5K5Oxw",  # Replace these with your Place IDs
    "ChIJrTLr-GyuEmsRBfy61i59si0",
]

def fetch_place_details(place_id):
    """Fetch details about a place using the Google Maps API."""
    try:
        place = gmaps.place(place_id=place_id)
        result = place.get("result", {})
        return {
            "name": result.get("name"),
            "address": result.get("formatted_address"),
            "phone": result.get("formatted_phone_number"),
            "website": result.get("website"),
            "rating": result.get("rating"),
            "reviews": result.get("user_ratings_total"),
            "notes": markdownify(result.get("editorial_summary", {}).get("overview", ""))
        }
    except Exception as e:
        print(f"Error fetching details for Place ID {place_id}: {e}")
        return None

def create_markdown_file(place_details):
    """Create a Markdown file for a place."""
    if not place_details:
        return
    filename = f"{place_details['name'].replace(' ', '_').replace('/', '-')}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)
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
    print(f"Markdown file created: {filepath}")

def main():
    """Main function to fetch details and create markdown notes."""
    for place_id in saved_places:
        print(f"Fetching details for Place ID: {place_id}")
        details = fetch_place_details(place_id)
        create_markdown_file(details)

if __name__ == "__main__":
    main()

