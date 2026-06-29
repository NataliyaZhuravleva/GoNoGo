# © 2026 Nataliya Zhuravleva. All rights reserved.
from gonogo.rules import (
    evaluate_cell,
    evaluate_cloud_cover,
    evaluate_freezing_level,
    evaluate_precipitation,
    evaluate_visibility,
    evaluate_wind,
    get_worst_color,
)

def test_evaluate_wind():
    # Green threshold: < 15 mph
    assert evaluate_wind(0.0)["color"] == "Green"
    assert evaluate_wind(14.9)["color"] == "Green"
    
    # Yellow threshold: 15 <= wind <= 30 mph
    assert evaluate_wind(15.0)["color"] == "Yellow"
    assert evaluate_wind(30.0)["color"] == "Yellow"
    
    # Red threshold: > 30 mph
    assert evaluate_wind(30.1)["color"] == "Red"
    assert evaluate_wind(50.0)["color"] == "Red"

def test_evaluate_precipitation():
    # Green threshold: <= 0.01 mm/h
    assert evaluate_precipitation(0.0, 40.0)["color"] == "Green"
    assert evaluate_precipitation(0.01, 20.0)["color"] == "Green"
    
    # Yellow threshold (Snow, temp <= 32F): 0.01 < precip <= 2.5 mm/h
    assert evaluate_precipitation(1.0, 30.0)["color"] == "Yellow"
    assert evaluate_precipitation(2.5, 32.0)["color"] == "Yellow"
    
    # Red threshold (Snow): > 2.5 mm/h
    assert evaluate_precipitation(2.6, 30.0)["color"] == "Red"
    
    # Yellow threshold (Rain, temp > 32F): 0.01 < precip <= 1.5 mm/h
    assert evaluate_precipitation(0.5, 40.0)["color"] == "Yellow"
    assert evaluate_precipitation(1.5, 40.0)["color"] == "Yellow"
    
    # Red threshold (Rain): > 1.5 mm/h
    assert evaluate_precipitation(1.6, 35.0)["color"] == "Red"

def test_evaluate_freezing_level():
    # Green threshold: below tier or < 1,000 ft above
    assert evaluate_freezing_level(5000.0, 5000.0)["color"] == "Green"
    assert evaluate_freezing_level(4000.0, 5000.0)["color"] == "Green"
    assert evaluate_freezing_level(5999.0, 5000.0)["color"] == "Green"
    
    # Yellow threshold: 1,000 to 3,000 ft above
    assert evaluate_freezing_level(6000.0, 5000.0)["color"] == "Yellow"
    assert evaluate_freezing_level(8000.0, 5000.0)["color"] == "Yellow"
    
    # Red threshold: > 3,000 ft above
    assert evaluate_freezing_level(8001.0, 5000.0)["color"] == "Red"
    assert evaluate_freezing_level(10000.0, 5000.0)["color"] == "Red"

def test_evaluate_visibility():
    # Green threshold: >= 10,000m
    assert evaluate_visibility(10000.0)["color"] == "Green"
    assert evaluate_visibility(15000.0)["color"] == "Green"
    
    # Yellow threshold: 3,000m <= vis < 10,000m
    assert evaluate_visibility(3000.0)["color"] == "Yellow"
    assert evaluate_visibility(9999.0)["color"] == "Yellow"
    
    # Red threshold: < 3,000m
    assert evaluate_visibility(2999.0)["color"] == "Red"
    assert evaluate_visibility(500.0)["color"] == "Red"

def test_evaluate_cloud_cover():
    # Green threshold: < 30%
    assert evaluate_cloud_cover(0.0)["color"] == "Green"
    assert evaluate_cloud_cover(29.9)["color"] == "Green"
    
    # Yellow threshold: 30% <= cloud <= 80%
    assert evaluate_cloud_cover(30.0)["color"] == "Yellow"
    assert evaluate_cloud_cover(80.0)["color"] == "Yellow"
    
    # Red threshold: > 80%
    assert evaluate_cloud_cover(80.1)["color"] == "Red"
    assert evaluate_cloud_cover(100.0)["color"] == "Red"

def test_get_worst_color():
    assert get_worst_color(["Green", "Green"]) == "Green"
    assert get_worst_color(["Green", "Yellow", "Green"]) == "Yellow"
    assert get_worst_color(["Green", "Yellow", "Red"]) == "Red"

def test_evaluate_cell_composite():
    # All Green parameters
    verdict = evaluate_cell(
        temp_f=30.0,
        precip_mm=0.0,
        wind_speed_mph=10.0,
        cloud_cover_pct=20.0,
        visibility_m=12000.0,
        freezing_level_ft=4500.0,
        tier_elevation_ft=5000.0
    )
    assert verdict["composite_color"] == "Green"
    
    # One Yellow parameter (wind), others Green
    verdict = evaluate_cell(
        temp_f=30.0,
        precip_mm=0.0,
        wind_speed_mph=20.0,
        cloud_cover_pct=20.0,
        visibility_m=12000.0,
        freezing_level_ft=4500.0,
        tier_elevation_ft=5000.0
    )
    assert verdict["composite_color"] == "Yellow"
    assert verdict["wind"]["color"] == "Yellow"
    
    # One Red parameter (rain), others Green
    verdict = evaluate_cell(
        temp_f=35.0,  # above freezing
        precip_mm=2.0, # rain! (above 1.5 limit)
        wind_speed_mph=10.0,
        cloud_cover_pct=20.0,
        visibility_m=12000.0,
        freezing_level_ft=4500.0,
        tier_elevation_ft=5000.0
    )
    assert verdict["composite_color"] == "Red"
    assert verdict["precipitation"]["color"] == "Red"
