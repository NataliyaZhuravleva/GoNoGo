# © 2026 Nataliya Zhuravleva. All rights reserved.
from typing import TypedDict

class MetricVerdict(TypedDict):
    color: str
    reason: str

class CellVerdict(TypedDict):
    composite_color: str
    wind: MetricVerdict
    precipitation: MetricVerdict
    freezing_level: MetricVerdict
    visibility: MetricVerdict
    cloud_cover: MetricVerdict

def evaluate_wind(wind_speed_mph: float) -> MetricVerdict:
    """Evaluate wind speed on exposed terrain."""
    if wind_speed_mph < 15.0:
        return {"color": "Green", "reason": f"Calm/light winds ({wind_speed_mph:.1f} mph)"}
    elif wind_speed_mph <= 30.0:
        return {"color": "Yellow", "reason": f"Moderate winds ({wind_speed_mph:.1f} mph), watch exposure"}
    else:
        return {"color": "Red", "reason": f"High winds ({wind_speed_mph:.1f} mph), dangerous on ridges"}

def evaluate_precipitation(precip_mm: float, temp_f: float) -> MetricVerdict:
    """Evaluate precipitation type and intensity."""
    if precip_mm <= 0.01:
        return {"color": "Green", "reason": "No precipitation"}
    
    is_rain = temp_f > 32.0
    
    if is_rain:
        # Rain is highly discouraged in mountaineering (wet out, snow instability)
        if precip_mm <= 1.5:
            return {"color": "Yellow", "reason": f"Light rain/drizzle ({precip_mm:.2f} mm/h)"}
        else:
            return {"color": "Red", "reason": f"Moderate/heavy rain ({precip_mm:.2f} mm/h)"}
    else:
        # Snow conditions
        if precip_mm <= 2.5:
            return {"color": "Yellow", "reason": f"Light snow ({precip_mm:.2f} mm/h)"}
        else:
            return {"color": "Red", "reason": f"Heavy snow ({precip_mm:.2f} mm/h), high accumulation risk"}

def evaluate_freezing_level(freezing_level_ft: float, tier_elevation_ft: float) -> MetricVerdict:
    """Evaluate freezing level relative to the tier elevation."""
    if freezing_level_ft <= tier_elevation_ft:
        return {"color": "Green", "reason": f"Freezing level ({freezing_level_ft:.0f} ft) is below tier ({tier_elevation_ft:.0f} ft)"}
    
    diff = freezing_level_ft - tier_elevation_ft
    if diff < 1000.0:
        return {"color": "Green", "reason": f"Freezing level ({freezing_level_ft:.0f} ft) is close to tier ({tier_elevation_ft:.0f} ft)"}
    elif diff <= 3000.0:
        return {"color": "Yellow", "reason": f"Freezing level ({freezing_level_ft:.0f} ft) is {diff:.0f} ft above tier (moderate melting)"}
    else:
        return {"color": "Red", "reason": f"Freezing level ({freezing_level_ft:.0f} ft) is {diff:.0f} ft above tier (high rockfall/wet avalanche risk)"}

def evaluate_visibility(visibility_meters: float) -> MetricVerdict:
    """Evaluate visibility."""
    if visibility_meters >= 10000.0:
        return {"color": "Green", "reason": f"Good visibility ({visibility_meters / 1000.0:.1f} km)"}
    elif visibility_meters >= 3000.0:
        return {"color": "Yellow", "reason": f"Moderate visibility ({visibility_meters / 1000.0:.1f} km)"}
    else:
        return {"color": "Red", "reason": f"Low visibility ({visibility_meters / 1000.0:.1f} km), navigation risk"}

def evaluate_cloud_cover(cloud_cover_pct: float) -> MetricVerdict:
    """Evaluate cloud cover."""
    if cloud_cover_pct < 30.0:
        return {"color": "Green", "reason": f"Clear/mostly clear ({cloud_cover_pct:.0f}%)"}
    elif cloud_cover_pct <= 80.0:
        return {"color": "Yellow", "reason": f"Partly/mostly cloudy ({cloud_cover_pct:.0f}%)"}
    else:
        return {"color": "Red", "reason": f"Overcast/foggy ({cloud_cover_pct:.0f}%), whiteout risk"}

def get_worst_color(colors: list[str]) -> str:
    """Determine the worst color in a list based on priority: Red > Yellow > Green."""
    if "Red" in colors:
        return "Red"
    if "Yellow" in colors:
        return "Yellow"
    return "Green"

def evaluate_cell(
    temp_f: float,
    precip_mm: float,
    wind_speed_mph: float,
    cloud_cover_pct: float,
    visibility_m: float,
    freezing_level_ft: float,
    tier_elevation_ft: float
) -> CellVerdict:
    """Evaluate all conditions for a single cell (day-part at a specific tier)."""
    wind_verdict = evaluate_wind(wind_speed_mph)
    precip_verdict = evaluate_precipitation(precip_mm, temp_f)
    freezing_verdict = evaluate_freezing_level(freezing_level_ft, tier_elevation_ft)
    visibility_verdict = evaluate_visibility(visibility_m)
    cloud_verdict = evaluate_cloud_cover(cloud_cover_pct)
    
    composite = get_worst_color([
        wind_verdict["color"],
        precip_verdict["color"],
        freezing_verdict["color"],
        visibility_verdict["color"],
        cloud_verdict["color"]
    ])
    
    return {
        "composite_color": composite,
        "wind": wind_verdict,
        "precipitation": precip_verdict,
        "freezing_level": freezing_verdict,
        "visibility": visibility_verdict,
        "cloud_cover": cloud_verdict
    }
