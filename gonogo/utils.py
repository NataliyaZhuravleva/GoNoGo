# © 2026 Nataliya Zhuravleva. All rights reserved.
from datetime import date, datetime


def feet_to_meters(feet: float) -> float:
    """Convert feet to meters."""
    return feet * 0.3048


def meters_to_feet(meters: float) -> float:
    """Convert meters to feet."""
    return meters * 3.280839895


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return (celsius * 9 / 5) + 32


def kmh_to_mph(kmh: float) -> float:
    """Convert kilometers per hour to miles per hour."""
    return kmh * 0.621371192


def parse_date(date_str: str) -> date:
    """Parse a YYYY-MM-DD string into a datetime.date object.

    Raises:
        ValueError: If the string is not in YYYY-MM-DD format.
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(
            f"Invalid date format '{date_str}'. Expected YYYY-MM-DD."
        ) from e
