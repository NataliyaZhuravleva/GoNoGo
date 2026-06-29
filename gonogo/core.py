# © 2026 Nataliya Zhuravleva. All rights reserved.
import json
import os
from datetime import date, timedelta
from typing import Any

import httpx
from pydantic import BaseModel

from gonogo.rules import CellVerdict, evaluate_cell, get_worst_color
from gonogo.utils import (
    celsius_to_fahrenheit,
    feet_to_meters,
    kmh_to_mph,
    meters_to_feet,
    parse_date,
)

# --- Pydantic Data Models ---


class DayParts(BaseModel):
    morning: CellVerdict
    midday: CellVerdict
    evening: CellVerdict


class DailyForecast(BaseModel):
    date: str
    parts: DayParts


class TierForecast(BaseModel):
    tier_name: str
    elevation_ft: float
    forecast_days: list[DailyForecast]
    composite_color: str


class RegionForecast(BaseModel):
    region_id: str
    region_name: str
    headline_peak_name: str
    headline_peak_lat: float
    headline_peak_lon: float
    past_48h_precip_mm: float
    tiers: dict[str, TierForecast]  # keys: "base", "mid", "peak"


# --- File and Data Helpers ---


def get_data_path() -> str:
    """Get the absolute path to regions.json."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(current_dir, ".."))
    return os.path.join(root_dir, "data", "regions.json")


def load_regions_data() -> list[dict[str, Any]]:
    """Load the regions data from regions.json and sort north-to-south by headline peak latitude."""
    path = get_data_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f"regions.json not found at {path}")
    with open(path, encoding="utf-8") as f:
        regions = json.load(f)

    # Sort regions north-to-south by the latitude of their headline peak
    def get_lat(region: dict[str, Any]) -> float:
        peak = get_headline_peak(region)
        return peak["coordinates"]["lat"]

    regions.sort(key=get_lat, reverse=True)
    return regions


def get_headline_peak(region: dict[str, Any]) -> dict[str, Any]:
    """Find and return the headline peak object for a region."""
    headline_id = region.get("headline_peak_id")
    for peak in region.get("peaks", []):
        if peak.get("peak_id") == headline_id:
            return peak
    raise ValueError(
        f"Headline peak '{headline_id}' not found in region '{region.get('name')}'"
    )


# --- Date Guardrail ---


def validate_and_clamp_date_range(
    start_date_str: str,
    end_date_str: str | None = None,
    current_date: date | None = None,
) -> tuple[date, date, str | None]:
    """Validate and clamp the requested date range.

    Rules:
    1. Parse start and end dates. If end_date is None, default to start_date + 2 days (3-day forecast).
    2. Start date cannot be in the past (before current_date).
    3. Start date must be within 7 days of current_date (reliable forecast horizon).
    4. End date cannot be before start date.
    5. Capped at 7 days. If range is > 7 days, clamp it to 7 days and return a warning message.

    Returns:
        tuple: (validated_start_date, validated_end_date, warning_message_or_None)
    """
    if current_date is None:
        current_date = date.today()

    start_date = parse_date(start_date_str)

    # Rule 2: Start date in the past
    if start_date < current_date:
        raise ValueError(
            f"Requested start date {start_date} is in the past. Current date is {current_date}."
        )

    # Rule 3: Start date too far in the future
    if (start_date - current_date).days > 7:
        raise ValueError(
            f"Requested start date {start_date} is beyond the 7-day reliable forecast horizon (limit: {current_date + timedelta(days=7)})."
        )

    if end_date_str:
        end_date = parse_date(end_date_str)
    else:
        # Default: 3-day forecast starting on start_date
        end_date = start_date + timedelta(days=2)

    # Rule 4: End date before start date
    if end_date < start_date:
        raise ValueError(
            f"End date {end_date} cannot be before start date {start_date}."
        )

    # Rule 5: Capped at 7 days
    duration_days = (end_date - start_date).days + 1
    warning_msg = None
    if duration_days > 7:
        end_date = start_date + timedelta(days=6)
        warning_msg = (
            f"Requested range of {duration_days} days exceeds the 7-day limit. "
            f"Clamped range to 7 days: {start_date} to {end_date}."
        )

    return start_date, end_date, warning_msg


# --- Open-Meteo Batched Fetcher ---


def fetch_conditions(start_date: date, end_date: date) -> list[RegionForecast]:
    """Fetch conditions from Open-Meteo for all 12 regions and 3 tiers in one batched request.

    Args:
        start_date: Start date of the forecast range.
        end_date: End date of the forecast range.

    Returns:
        List[RegionForecast] sorted north-to-south.
    """
    regions = load_regions_data()

    # Scope Guardrail: Verify that only the authorized 12 region IDs are computed
    allowed_ids = {
        "baker_shuksan",
        "washington_pass",
        "stuart_enchantments",
        "glacier_peak",
        "eldorado_cascade_pass",
        "rainier",
        "south_wa_volcanoes",
        "hood",
        "jefferson_three_sisters",
        "mt_olympus",
        "eastern_olympics",
        "shasta",
    }
    loaded_ids = {r["region_id"] for r in regions}
    if not loaded_ids.issubset(allowed_ids):
        raise ValueError(
            f"Scope Guardrail Violation: Detected unauthorized region(s): {loaded_ids - allowed_ids}"
        )

    # Build 36 coordinate-elevation pairs
    # Keep track of mapping: index -> (region, tier_key, elevation_ft)
    query_mapping: list[tuple[dict[str, Any], str, float]] = []

    lats: list[float] = []
    lons: list[float] = []
    elevs_m: list[float] = []

    for region in regions:
        headline = get_headline_peak(region)
        lat = headline["coordinates"]["lat"]
        lon = headline["coordinates"]["lon"]

        for tier_key in ["base", "mid", "peak"]:
            tier_info = region["tiers"][tier_key]
            elev_ft = tier_info["elev_ft"]
            elev_m = feet_to_meters(elev_ft)

            lats.append(lat)
            lons.append(lon)
            elevs_m.append(elev_m)
            query_mapping.append((region, tier_key, elev_ft))

    # Open-Meteo API Call
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": ",".join(str(lat) for lat in lats),
        "longitude": ",".join(str(lon) for lon in lons),
        "elevation": ",".join(str(round(e)) for e in elevs_m),
        "hourly": "temperature_2m,precipitation,wind_speed_10m,wind_gusts_10m,cloud_cover,visibility,freezing_level_height",
        "timezone": "America/Los_Angeles",
        "past_days": 2,
    }

    # Execute single GET request
    response = httpx.get(url, params=params, timeout=30.0)
    response.raise_for_status()

    raw_data = response.json()
    if not isinstance(raw_data, list):
        # Open-Meteo returns a single dictionary if only one coordinate is requested,
        # but for multiple coordinates it returns a list of dictionaries.
        # Since we query 36 coordinates, it should always be a list.
        raw_data = [raw_data]

    # Process responses and group by region and tier
    # Prepare date range list
    date_list: list[date] = []
    curr = start_date
    while curr <= end_date:
        date_list.append(curr)
        curr += timedelta(days=1)

    # Temporary structures to build the final list
    # region_id -> RegionForecast draft
    region_forecasts: dict[str, dict] = {}

    for idx, resp in enumerate(raw_data):
        region_info, tier_key, elev_ft = query_mapping[idx]
        region_id = region_info["region_id"]

        # Initialize region draft if not present
        if region_id not in region_forecasts:
            headline = get_headline_peak(region_info)
            region_forecasts[region_id] = {
                "region_id": region_id,
                "region_name": region_info["name"],
                "headline_peak_name": headline["name"],
                "headline_peak_lat": headline["coordinates"]["lat"],
                "headline_peak_lon": headline["coordinates"]["lon"],
                "past_48h_precip_mm": 0.0,
                "tiers": {},
            }

        hourly = resp["hourly"]
        times = hourly["time"]
        temps_c = hourly["temperature_2m"]
        precips = hourly["precipitation"]
        winds_kmh = hourly["wind_speed_10m"]
        gusts_kmh = hourly.get("wind_gusts_10m")
        clouds = hourly["cloud_cover"]
        visibilities = hourly["visibility"]
        freezing_m = hourly["freezing_level_height"]

        # Calculate past 48h precipitation (first 48 elements represents past_days=2)
        # Open-Meteo's hourly array prepends exactly 48 hours for past_days=2
        past_precip = sum(precips[:48])

        # If this is the 'peak' tier, set the region's past 48h precipitation badge
        if tier_key == "peak":
            region_forecasts[region_id]["past_48h_precip_mm"] = past_precip

        # Parse forecast days
        forecast_days: list[DailyForecast] = []
        tier_colors: list[str] = []

        for d in date_list:
            # Fetch for AM (08:00), PM (14:00), Night (22:00) local time
            day_verdicts = {}
            for part, hour in [("morning", 8), ("midday", 14), ("evening", 22)]:
                target_str = f"{d.isoformat()}T{hour:02d}:00"
                try:
                    t_idx = times.index(target_str)

                    t_f = celsius_to_fahrenheit(temps_c[t_idx])
                    p_mm = precips[t_idx]
                    sustained_mph = kmh_to_mph(winds_kmh[t_idx])
                    gust_mph = (
                        kmh_to_mph(gusts_kmh[t_idx])
                        if gusts_kmh is not None and gusts_kmh[t_idx] is not None
                        else None
                    )
                    w_mph = (
                        max(sustained_mph, gust_mph)
                        if gust_mph is not None
                        else sustained_mph
                    )
                    is_gust = gust_mph is not None and gust_mph > sustained_mph
                    cloud_pct = clouds[t_idx]
                    vis_m = visibilities[t_idx]
                    freezing_ft = meters_to_feet(freezing_m[t_idx])

                    cell_verdict = evaluate_cell(
                        temp_f=t_f,
                        precip_mm=p_mm,
                        wind_speed_mph=w_mph,
                        wind_is_gust=is_gust,
                        cloud_cover_pct=cloud_pct,
                        visibility_m=vis_m,
                        freezing_level_ft=freezing_ft,
                        tier_elevation_ft=elev_ft,
                        tier_key=tier_key,
                    )
                except (ValueError, KeyError, IndexError):
                    # Fallback default if data missing
                    cell_verdict = {
                        "composite_color": "Red",
                        "wind": {"color": "Red", "reason": "Data unavailable"},
                        "precipitation": {"color": "Red", "reason": "Data unavailable"},
                        "freezing_level": {
                            "color": "Red",
                            "reason": "Data unavailable",
                        },
                        "visibility": {"color": "Red", "reason": "Data unavailable"},
                        "cloud_cover": {"color": "Red", "reason": "Data unavailable"},
                    }

                day_verdicts[part] = cell_verdict
                tier_colors.append(cell_verdict["composite_color"])

            forecast_days.append(
                DailyForecast(date=d.isoformat(), parts=DayParts(**day_verdicts))
            )

        tier_comp_color = get_worst_color(tier_colors)

        region_forecasts[region_id]["tiers"][tier_key] = TierForecast(
            tier_name=tier_key.capitalize(),
            elevation_ft=elev_ft,
            forecast_days=forecast_days,
            composite_color=tier_comp_color,
        )

    # Reassemble in the exact sorted region order
    sorted_forecasts: list[RegionForecast] = []
    for region in regions:
        r_id = region["region_id"]
        sorted_forecasts.append(RegionForecast(**region_forecasts[r_id]))

    return sorted_forecasts
