# © 2026 Nataliya Zhuravleva. All rights reserved.
import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from gonogo.core import fetch_conditions
from gonogo.rules import evaluate_cell

def make_mock_hourly(
    temp_c: float,
    precip_mm: float,
    wind_kmh: float,
    cloud_pct: float,
    vis_m: float,
    freezing_m: float,
    start_date: date,
    end_date: date,
    past_precip_value: float = 0.0
) -> dict:
    """Generate mock hourly data for Open-Meteo responses.
    Includes 48 hours of past data and full hourly series for forecast days.
    """
    times = []
    # 48 hours of past data
    past_start = start_date - timedelta(days=2)
    for d_idx in range(2):
        curr_d = past_start + timedelta(days=d_idx)
        for h in range(24):
            times.append(f"{curr_d.isoformat()}T{h:02d}:00")
            
    # Forecast days
    curr_d = start_date
    while curr_d <= end_date:
        for h in range(24):
            times.append(f"{curr_d.isoformat()}T{h:02d}:00")
        curr_d += timedelta(days=1)
        
    num_hours = len(times)
    
    # Fill precip: past 48h gets past_precip_value / 48 per hour, rest gets precip_mm
    precip_series = [past_precip_value / 48.0] * 48 + [precip_mm] * (num_hours - 48)
    
    return {
        "hourly": {
            "time": times,
            "temperature_2m": [temp_c] * num_hours,
            "precipitation": precip_series,
            "wind_speed_10m": [wind_kmh] * num_hours,
            "cloud_cover": [cloud_pct] * num_hours,
            "visibility": [vis_m] * num_hours,
            "freezing_level_height": [freezing_m] * num_hours
        }
    }

@pytest.mark.anyio
@patch("gonogo.core.load_regions_data")
@patch("httpx.get")
def test_golden_scenario_bluebird(mock_get, mock_load_regions):
    """Scenario 1: Ideal Bluebird Day
    - Cool temp (5°C = 41°F)
    - Calm winds (10 km/h = 6.2 mph)
    - No precipitation
    - Clear skies (10% cloud cover)
    - High visibility (15,000m)
    - Low freezing level (1,500m = ~4,921 ft)
    Expected result: Green for all tiers, overall color Green.
    """
    start = date(2026, 6, 26)
    end = date(2026, 6, 26)
    
    # Mock single region: Mt. Baker / Mt. Shuksan
    mock_region = {
        "region_id": "baker_shuksan",
        "name": "Mt. Baker / Mt. Shuksan",
        "headline_peak_id": "mt_baker",
        "peaks": [
            {
                "peak_id": "mt_baker",
                "name": "Mt. Baker",
                "is_headline": True,
                "coordinates": {"lat": 48.7767, "lon": -121.8144}
            }
        ],
        "tiers": {
            "base": {"elev_ft": 3000.0},
            "mid": {"elev_ft": 6000.0},
            "peak": {"elev_ft": 10000.0}
        }
    }
    mock_load_regions.return_value = [mock_region]
    
    # 3 tiers = 3 response objects in list
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        make_mock_hourly(5.0, 0.0, 10.0, 10.0, 15000.0, 500.0, start, end), # base (freezing level 500m = 1640 ft, below 3000 ft -> Green)
        make_mock_hourly(5.0, 0.0, 10.0, 10.0, 15000.0, 500.0, start, end), # mid (freezing level 500m = 1640 ft, below 6000 ft -> Green)
        make_mock_hourly(5.0, 0.0, 10.0, 10.0, 15000.0, 500.0, start, end)  # peak (freezing level 500m = 1640 ft, below 10000 ft -> Green)
    ]
    mock_get.return_value = mock_resp
    
    forecasts = fetch_conditions(start, end)
    assert len(forecasts) == 1
    f = forecasts[0]
    assert f.region_id == "baker_shuksan"
    
    # Verify overall colors
    assert f.tiers["base"].composite_color == "Green"
    assert f.tiers["mid"].composite_color == "Green"
    assert f.tiers["peak"].composite_color == "Green"

@pytest.mark.anyio
@patch("gonogo.core.load_regions_data")
@patch("httpx.get")
def test_golden_scenario_high_wind(mock_get, mock_load_regions):
    """Scenario 2: High Wind Hazard
    - Wind is 60 km/h (~37.3 mph) at peak.
    Expected result: Peak tier should be Red due to high wind.
    """
    start = date(2026, 6, 26)
    end = date(2026, 6, 26)
    
    mock_region = {
        "region_id": "baker_shuksan",
        "name": "Mt. Baker / Mt. Shuksan",
        "headline_peak_id": "mt_baker",
        "peaks": [
            {
                "peak_id": "mt_baker",
                "name": "Mt. Baker",
                "is_headline": True,
                "coordinates": {"lat": 48.7767, "lon": -121.8144}
            }
        ],
        "tiers": {
            "base": {"elev_ft": 3000.0},
            "mid": {"elev_ft": 6000.0},
            "peak": {"elev_ft": 10000.0}
        }
    }
    mock_load_regions.return_value = [mock_region]
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        make_mock_hourly(5.0, 0.0, 10.0, 10.0, 15000.0, 1000.0, start, end), # base (wind 10 km/h -> green)
        make_mock_hourly(5.0, 0.0, 10.0, 10.0, 15000.0, 1000.0, start, end), # mid (wind 10 km/h -> green)
        make_mock_hourly(5.0, 0.0, 60.0, 10.0, 15000.0, 1000.0, start, end)  # peak (wind 60 km/h -> red)
    ]
    mock_get.return_value = mock_resp
    
    forecasts = fetch_conditions(start, end)
    f = forecasts[0]
    
    assert f.tiers["base"].composite_color == "Green"
    assert f.tiers["peak"].composite_color == "Red"
    
    # Verify that the peak tier's morning wind metric is Red
    assert f.tiers["peak"].forecast_days[0].parts.morning["wind"]["color"] == "Red"

@pytest.mark.anyio
@patch("gonogo.core.load_regions_data")
@patch("httpx.get")
def test_golden_scenario_warm_freezing_level(mock_get, mock_load_regions):
    """Scenario 3: Warm Freezing Level / Rockfall Risk
    - Freezing level is 5,000m (~16,400 ft), while peak is 10,000 ft.
    - Difference is ~6,400 ft, which is > 3000 ft.
    Expected result: Peak tier should be Red due to warm freezing level / melting.
    """
    start = date(2026, 6, 26)
    end = date(2026, 6, 26)
    
    mock_region = {
        "region_id": "baker_shuksan",
        "name": "Mt. Baker / Mt. Shuksan",
        "headline_peak_id": "mt_baker",
        "peaks": [
            {
                "peak_id": "mt_baker",
                "name": "Mt. Baker",
                "is_headline": True,
                "coordinates": {"lat": 48.7767, "lon": -121.8144}
            }
        ],
        "tiers": {
            "base": {"elev_ft": 3000.0},
            "mid": {"elev_ft": 6000.0},
            "peak": {"elev_ft": 10000.0}
        }
    }
    mock_load_regions.return_value = [mock_region]
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        make_mock_hourly(5.0, 0.0, 10.0, 10.0, 15000.0, 5000.0, start, end), # base (elev 3000, freezing 16400, diff 13400 -> red)
        make_mock_hourly(5.0, 0.0, 10.0, 10.0, 15000.0, 5000.0, start, end), # mid (elev 6000, freezing 16400, diff 10400 -> red)
        make_mock_hourly(5.0, 0.0, 10.0, 10.0, 15000.0, 5000.0, start, end)  # peak (elev 10000, freezing 16400, diff 6400 -> red)
    ]
    mock_get.return_value = mock_resp
    
    forecasts = fetch_conditions(start, end)
    f = forecasts[0]
    
    assert f.tiers["peak"].composite_color == "Red"
    assert f.tiers["peak"].forecast_days[0].parts.morning["freezing_level"]["color"] == "Red"

@pytest.mark.anyio
@patch("gonogo.core.load_regions_data")
@patch("httpx.get")
def test_golden_scenario_rain_on_snow(mock_get, mock_load_regions):
    """Scenario 4: Rain on Snow / Wet Slide
    - Temp is 5°C (41°F)
    - Precipitation is 0.5 mm/h
    Expected result: Red due to rain at temperatures above freezing.
    """
    start = date(2026, 6, 26)
    end = date(2026, 6, 26)
    
    mock_region = {
        "region_id": "baker_shuksan",
        "name": "Mt. Baker / Mt. Shuksan",
        "headline_peak_id": "mt_baker",
        "peaks": [
            {
                "peak_id": "mt_baker",
                "name": "Mt. Baker",
                "is_headline": True,
                "coordinates": {"lat": 48.7767, "lon": -121.8144}
            }
        ],
        "tiers": {
            "base": {"elev_ft": 3000.0},
            "mid": {"elev_ft": 6000.0},
            "peak": {"elev_ft": 10000.0}
        }
    }
    mock_load_regions.return_value = [mock_region]
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        make_mock_hourly(5.0, 2.0, 10.0, 10.0, 15000.0, 100.0, start, end), # base (rain -> red)
        make_mock_hourly(5.0, 2.0, 10.0, 10.0, 15000.0, 100.0, start, end), # mid (rain -> red)
        make_mock_hourly(-5.0, 0.5, 10.0, 10.0, 15000.0, 100.0, start, end) # peak (snow at -5C/23F, 0.5 mm -> yellow)
    ]
    mock_get.return_value = mock_resp
    
    forecasts = fetch_conditions(start, end)
    f = forecasts[0]
    
    assert f.tiers["base"].composite_color == "Red"
    assert f.tiers["base"].forecast_days[0].parts.morning["precipitation"]["color"] == "Red"
    assert f.tiers["peak"].composite_color == "Yellow"

@pytest.mark.anyio
@patch("gonogo.core.load_regions_data")
@patch("httpx.get")
def test_golden_scenario_whiteout(mock_get, mock_load_regions):
    """Scenario 5: Whiteout / Low Visibility
    - Cloud cover is 95%
    - Visibility is 1,000 meters
    Expected result: Red due to low visibility and high cloud cover.
    """
    start = date(2026, 6, 26)
    end = date(2026, 6, 26)
    
    mock_region = {
        "region_id": "baker_shuksan",
        "name": "Mt. Baker / Mt. Shuksan",
        "headline_peak_id": "mt_baker",
        "peaks": [
            {
                "peak_id": "mt_baker",
                "name": "Mt. Baker",
                "is_headline": True,
                "coordinates": {"lat": 48.7767, "lon": -121.8144}
            }
        ],
        "tiers": {
            "base": {"elev_ft": 3000.0},
            "mid": {"elev_ft": 6000.0},
            "peak": {"elev_ft": 10000.0}
        }
    }
    mock_load_regions.return_value = [mock_region]
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        make_mock_hourly(5.0, 0.0, 10.0, 98.0, 1000.0, 100.0, start, end), # base (whiteout -> red)
        make_mock_hourly(5.0, 0.0, 10.0, 98.0, 1000.0, 100.0, start, end), # mid (whiteout -> red)
        make_mock_hourly(5.0, 0.0, 10.0, 98.0, 1000.0, 100.0, start, end)  # peak (whiteout -> red)
    ]
    mock_get.return_value = mock_resp
    
    forecasts = fetch_conditions(start, end)
    f = forecasts[0]
    
    assert f.tiers["base"].composite_color == "Red"
    assert f.tiers["base"].forecast_days[0].parts.morning["cloud_cover"]["color"] == "Red"
    assert f.tiers["base"].forecast_days[0].parts.morning["visibility"]["color"] == "Red"
