"""Residence tracking - determine default people/locations based on cohabitation and lived-in dates."""
import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass
from pkms.core.frontmatter import load_frontmatter_and_body
from pkms.core.vault import find_all_files


@dataclass
class ResidencePeriod:
    """Represents a period of cohabitation or residence."""
    file_path: str
    display_name: str
    start_date: datetime.date
    end_date: Optional[datetime.date]  # None = ongoing

    def includes_date(self, target_date: datetime.date) -> bool:
        """Check if target_date falls within this period."""
        if self.start_date <= target_date:
            return self.end_date is None or target_date <= self.end_date
        return False


class ResidenceCache:
    """Cache of all cohabitation and residence periods loaded once."""

    def __init__(self, people_path: Path, locations_path: Path):
        """Load all residence data once."""
        self.people_periods: List[ResidencePeriod] = []
        self.location_periods: List[ResidencePeriod] = []

        # Load people with cohabitation dates
        self._load_people(people_path)

        # Load locations with residence dates
        self._load_locations(locations_path)

    def _load_people(self, people_path: Path):
        """Load all people with cohabitation metadata."""
        for person_file in find_all_files(str(people_path)):
            if not person_file.endswith('.md'):
                continue

            try:
                fm, _ = load_frontmatter_and_body(person_file)
                if not isinstance(fm, dict):
                    continue

                start_str = fm.get('cohabitated_start')
                if not start_str:
                    continue

                start_date = parse_date(start_str)

                if not start_date:
                    continue

                end_str = fm.get('cohabitated_end')
                end_date = parse_date(end_str)

                display_name = person_file.split('/')[-1].replace('.md', '')
                period = ResidencePeriod(
                    file_path=person_file,
                    display_name=display_name,
                    start_date=start_date,
                    end_date=end_date
                )
                self.people_periods.append(period)

            except Exception as e:
                print(f"Error processing {person_file}: {e}")
                continue

    def _load_locations(self, locations_path: Path):
        """Load all locations with residence metadata."""
        for location_file in find_all_files(str(locations_path)):
            if not location_file.endswith('.md'):
                continue

            try:
                fm, _ = load_frontmatter_and_body(location_file)
                if not isinstance(fm, dict):
                    continue

                start_str = fm.get('lived_start')
                if not start_str:
                    continue

                start_date = parse_date(start_str)
                if not start_date:
                    continue

                end_str = fm.get('lived_end')
                end_date = parse_date(end_str) if end_str else None

                display_name = location_file.split('/')[-1].replace('.md', '')
                period = ResidencePeriod(
                    file_path=location_file,
                    display_name=display_name,
                    start_date=start_date,
                    end_date=end_date
                )
                self.location_periods.append(period)

            except Exception:
                continue

    def get_cohabitating_people(self, target_date: datetime.date) -> List[Tuple[str, str]]:
        """Get all people cohabitating on a specific date.

        Args:
            target_date: Date to check

        Returns:
            List of (file_path, display_name) tuples
        """
        return [
            (period.file_path, period.display_name)
            for period in self.people_periods
            if period.includes_date(target_date)
        ]

    def get_lived_in_locations(self, target_date: datetime.date) -> List[Tuple[str, str]]:
        """Get all locations where user lived on a specific date.

        Args:
            target_date: Date to check

        Returns:
            List of (file_path, display_name) tuples
        """
        return [
            (period.file_path, period.display_name)
            for period in self.location_periods
            if period.includes_date(target_date)
        ]

    def get_people_with_cohabitation(self) -> int:
        """Get count of people with cohabitation metadata."""
        return len(self.people_periods)

    def get_locations_with_residence(self) -> int:
        """Get count of locations with residence metadata."""
        return len(self.location_periods)


def parse_date(date_str: str | datetime.date) -> Optional[datetime.date]:
    """Parse a date string in YYYY-MM-DD format.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        datetime.date object or None if invalid
    """
    if not date_str:
        return None
    if isinstance(date_str, datetime.date):
        return date_str
    try:
        parts = date_str.split('-')
        if len(parts) == 3:
            return datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception as e:
        print(f"Invalid date string: {date_str} with error: {e}")
        pass
    return None


def get_default_people_for_date(cache: ResidenceCache, target_date: datetime.date) -> List[str]:
    """Get default people (cohabitating) for a date as wikilinks.

    Args:
        cache: ResidenceCache instance
        target_date: Date to get defaults for

    Returns:
        List of wikilink strings like [[path/to/person.md|Display Name]]
    """
    cohabitating = cache.get_cohabitating_people(target_date)
    wikilinks = []

    for person_file, display_name in cohabitating:
        # Create relative wikilink (assuming from pensieve/day perspective)
        rel_path = '/'.join(person_file.split('/')[-3:])  # e.g., people/family/Name.md
        wikilink = f"[[{rel_path}|{display_name}]]"
        wikilinks.append(wikilink)

    return wikilinks


def get_default_locations_for_date(cache: ResidenceCache, target_date: datetime.date) -> List[str]:
    """Get default locations (lived in) for a date as wikilinks.

    Args:
        cache: ResidenceCache instance
        target_date: Date to get defaults for

    Returns:
        List of wikilink strings like [[path/to/location.md|Display Name]]
    """
    lived_in = cache.get_lived_in_locations(target_date)
    wikilinks = []

    for location_file, display_name in lived_in:
        # Create relative wikilink (assuming from pensieve/day perspective)
        rel_path = '/'.join(location_file.split('/')[-2:])  # e.g., locations/City.md
        wikilink = f"[[{rel_path}|{display_name}]]"
        wikilinks.append(wikilink)

    return wikilinks


def should_add_default_people(existing_people: List[str], default_people: List[str]) -> List[str]:
    """Determine which default people should be added to a note.

    Only adds people who aren't already present.

    Args:
        existing_people: List of existing people wikilinks
        default_people: List of default people wikilinks to potentially add

    Returns:
        List of people to add (subset of default_people)
    """
    if not default_people:
        return []

    # Extract file paths from existing people links for comparison
    existing_paths = set()
    for person in existing_people:
        if isinstance(person, str) and '[[' in person:
            # Extract path from [[path|display]] or [[path]]
            path_part = person.split('[[')[1].split('|')[0].split(']]')[0]
            # Normalize path (remove leading ../../ etc)
            normalized = '/'.join(path_part.split('/')[-3:])  # Get last 3 parts
            existing_paths.add(normalized)

    # Only add defaults that aren't already present
    to_add = []
    for person in default_people:
        if '[[' in person:
            path_part = person.split('[[')[1].split('|')[0].split(']]')[0]
            normalized = '/'.join(path_part.split('/')[-3:])
            if normalized not in existing_paths:
                to_add.append(person)

    return to_add


def should_add_default_locations(existing_locations: List[str], default_locations: List[str]) -> List[str]:
    """Determine which default locations should be added to a note.

    Only adds locations that aren't already present.

    Args:
        existing_locations: List of existing location wikilinks
        default_locations: List of default location wikilinks to potentially add

    Returns:
        List of locations to add (subset of default_locations)
    """
    if not default_locations:
        return []

    # Extract location names from existing links for comparison
    existing_names = set()
    for location in existing_locations:
        if isinstance(location, str):
            # Extract display name from [[Location]] or [[path/Location|Display]]
            if '|' in location:
                name = location.split('|')[-1].strip(']')
            else:
                name = location.strip('[]').split('/')[-1].replace('.md', '')
            existing_names.add(name.lower())

    # Only add defaults that aren't already present
    to_add = []
    for location in default_locations:
        if '|' in location:
            name = location.split('|')[-1].strip(']')
        else:
            name = location.strip('[]').split('/')[-1].replace('.md', '')

        if name.lower() not in existing_names:
            to_add.append(location)

    return to_add


# Backward compatibility wrappers (deprecated - use ResidenceCache directly)
def get_cohabitating_people(people_path: Path, target_date: datetime.date) -> List[Tuple[str, str]]:
    """DEPRECATED: Use ResidenceCache instead. Get people cohabitating on a date."""
    cache = ResidenceCache(people_path, Path())
    return cache.get_cohabitating_people(target_date)


def get_lived_in_locations(locations_path: Path, target_date: datetime.date) -> List[Tuple[str, str]]:
    """DEPRECATED: Use ResidenceCache instead. Get locations lived in on a date."""
    cache = ResidenceCache(Path(), locations_path)
    return cache.get_lived_in_locations(target_date)
