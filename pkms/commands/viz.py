import click
from pkms.analytics.stats import person_timeline
from pkms.core import get_config
from pkms.core.vault import find_all_files
from pkms.core.frontmatter import load_frontmatter_and_body
import datetime
import json

@click.group()
def viz():
    """Visualize vault data."""
    pass

viz.add_command(person_timeline, name='person')

def extract_state(location_link):
    if not location_link:
        return ''
    if "locations/US" in location_link:
        parts = location_link.split("/")
        if len(parts) > 2:
            return parts[2].replace(".md]]", "").split('|')[-1].upper()
    return ''

@viz.command()
def locations():
    """Generate a heatmap of locations."""
    click.echo("Generating location heatmap...")
    config = get_config()
    files = find_all_files(str(config.pensieve_path))
    
    location_data = {}
    all_states = set()
    min_year, max_year = 0, 0

    state_colors = {
        "AL": "#ffa69e", "AK": "#4a4e69", "AZ": "#9a8c98", "AR": "#fcbf49", "CA": "#80ed99",
        "CO": "#00bbf9", "CT": "#7f96ff", "DE": "#ff99c8", "FL": "#bcece0", "GA": "#ff70a6",
        "HI": "#ffae03", "ID": "#4ecdc4", "IL": "#9d4edd", "IN": "#ff7b9c", "IA": "#6d597a",
        "KS": "#e5989b", "KY": "#457b9d", "LA": "#ff9a76", "ME": "#e5eaf5", "MD": "#70d6ff",
        "MA": "#f652a0", "MI": "#6a0572", "MN": "#48cae4", "MS": "#a2d2ff", "MO": "#ffb5a7",
        "MT": "#6f4a8e", "NE": "#ffcad4", "NV": "#1d3557", "NH": "#8ac6d1", "NJ": "#ff9a76",
        "NM": "#ffc09f", "NY": "#4c5270", "NC": "#ffcb77", "ND": "#8e9aaf", "OH": "#c77dff",
        "OK": "#f8ad9d", "OR": "#9a8c98", "PA": "#6b9080", "RI": "#36eee0", "SC": "#f9dbbd",
        "SD": "#118ab2", "TN": "#ef476f", "TX": "#ff7f50", "UT": "#ffd166", "VT": "#6a0572",
        "VA": "#90be6d", "WA": "#5f0f40", "WV": "#ff9770", "WI": "#b5838d", "WY": "#4a5759",
        "PR": "#f9bdc0", "Traveling": "#fbe698"
    }

    if files:
        dates = []
        for file_path in files:
            try:
                date_str = file_path.split('/')[-1].replace('.md', '')
                date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                dates.append(date)
            except ValueError:
                pass # Ignore files that are not named with a date
        
        if dates:
            min_year = min(dates).year
            max_year = max(dates).year

            start_date = datetime.date(min_year, 1, 1)
            end_date = datetime.date(max_year, 12, 31)
            delta = datetime.timedelta(days=1)
            current_date = start_date
            while current_date <= end_date:
                location_data[current_date.isoformat()] = None
                current_date += delta

    for file_path in files:
        try:
            fm, _ = load_frontmatter_and_body(file_path)
            date_str = file_path.split('/')[-1].replace('.md', '')
            date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            if 'locations' in fm and fm['locations']:
                locations = fm['locations']
                states = list(set([extract_state(loc) for loc in locations if extract_state(loc)]))
                if len(states) > 1:
                    location_data[date.isoformat()] = "Traveling"
                    all_states.add("Traveling")
                elif len(states) == 1:
                    state = states[0]
                    location_data[date.isoformat()] = state
                    all_states.add(state)
        except (ValueError, KeyError):
            pass
        except Exception as e:
            click.echo(f"An unexpected error occurred processing {file_path}: {e}", err=True)


    # Create a color map for the states
    color_map = {}
    for state in sorted(list(all_states)):
        if state in state_colors:
            color_map[state] = state_colors[state]
        else:
            # Assign a random color for unknown states
            color_map[state] = f'hsl({(len(color_map) * 360 / (len(all_states) + 1)) % 360}, 75%, 50%)'

    # Generate HTML
    html_content = generate_html(location_data, min_year, max_year, color_map)
    with open("locations.html", "w") as f:
        f.write(html_content)
    
    click.echo("Location heatmap saved to locations.html")

def generate_html(data, min_year, max_year, color_map):
    """Generate HTML for the location heatmap."""
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Location Heatmap</title>
        <script src="https://d3js.org/d3.v7.min.js"></script>
        <style>
            body {{
                font-family: sans-serif;
            }}
            #visualization {{
                display: flex;
                flex-direction: row;
            }}
            .year-container {{
                margin-right: 5px;
            }}
            .year-grid {{
                display: flex;
                flex-direction: column;
            }}
            .day-cell {{
                width: 10px;
                height: 10px;
            }}
            .tooltip {{
                position: absolute;
                background-color: #333;
                color: #fff;
                padding: 5px;
                border-radius: 3px;
                pointer-events: none;
                opacity: 0;
            }}
            .legend {{
                margin-bottom: 10px;
            }}
            .legend-item {{
                display: inline-block;
                margin-right: 5px;
            }}
            .legend-color {{
                width: 10px;
                height: 10px;
                display: inline-block;
            }}
        </style>
    </head>
    <body>
        <div class="legend">
            {''.join([f'<div class="legend-item"><div class="legend-color" style="background-color: {color};"></div></div>' for color in color_map.values()])}
        </div>
        <div id="visualization"></div>
        <div class="tooltip"></div>

        <script>
            const data = {json.dumps(data)};
            const colorMap = {json.dumps(color_map)};
            const minYear = {min_year};
            const maxYear = {max_year};

            const visualization = d3.select("#visualization");
            const tooltip = d3.select(".tooltip");

            for (let year = minYear; year <= maxYear; year++) {{
                const yearData = Object.entries(data).filter(([date]) => date.startsWith(year.toString()));
                
                const yearContainer = visualization.append("div").attr("class", "year-container");
                const yearGrid = yearContainer.append("div").attr("class", "year-grid");

                yearGrid.selectAll(".day-cell")
                    .data(yearData)
                    .enter()
                    .append("div")
                    .attr("class", "day-cell")
                    .style("background-color", d => colorMap[d[1]] || "#efefef")
                    .on("mouseover", (event, d) => {{
                        tooltip.transition().duration(200).style("opacity", .9);
                        tooltip.html(d[1] || "No location")
                            .style("left", (event.pageX) + "px")
                            .style("top", (event.pageY - 28) + "px");
                    }})
                    .on("mouseout", d => {{
                        tooltip.transition().duration(500).style("opacity", 0);
                    }});
            }}
        </script>
    </body>
    </html>
    """