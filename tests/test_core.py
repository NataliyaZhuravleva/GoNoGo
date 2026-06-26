# © 2026 Nataliya Zhuravleva. All rights reserved.
from datetime import date, timedelta
import pytest

from gonogo.core import (
    get_headline_peak,
    load_regions_data,
    validate_and_clamp_date_range,
)

def test_load_regions_data_and_sorting():
    regions = load_regions_data()
    assert len(regions) == 12
    
    # Verify sorted descending by latitude of headline peak (North to South)
    for i in range(len(regions) - 1):
        lat1 = get_headline_peak(regions[i])["coordinates"]["lat"]
        lat2 = get_headline_peak(regions[i + 1])["coordinates"]["lat"]
        assert lat1 >= lat2, f"Regions not sorted north-to-south: {regions[i]['name']} ({lat1}) vs {regions[i+1]['name']} ({lat2})"

def test_get_headline_peak():
    regions = load_regions_data()
    # Test Mt. Baker region
    baker_region = next(r for r in regions if r["region_id"] == "baker_shuksan")
    headline = get_headline_peak(baker_region)
    assert headline["peak_id"] == "mt_baker"
    assert headline["is_headline"] is True
    
    # Test Stuart Range region
    stuart_region = next(r for r in regions if r["region_id"] == "stuart_enchantments")
    headline = get_headline_peak(stuart_region)
    assert headline["peak_id"] == "mt_stuart"
    assert headline["is_headline"] is True

def test_date_range_guardrails():
    # Setup mock current date
    ref_date = date(2026, 6, 25)
    
    # Test valid 3-day default range starting tomorrow
    start, end, warning = validate_and_clamp_date_range("2026-06-26", current_date=ref_date)
    assert start == date(2026, 6, 26)
    assert end == date(2026, 6, 28)
    assert warning is None
    
    # Test valid custom range
    start, end, warning = validate_and_clamp_date_range("2026-06-26", "2026-06-30", current_date=ref_date)
    assert start == date(2026, 6, 26)
    assert end == date(2026, 6, 30)
    assert warning is None
    
    # Test start date in the past
    with pytest.raises(ValueError, match="is in the past"):
        validate_and_clamp_date_range("2026-06-24", current_date=ref_date)
        
    # Test start date too far in future (> 7 days)
    with pytest.raises(ValueError, match="beyond the 7-day reliable forecast horizon"):
        validate_and_clamp_date_range("2026-07-05", current_date=ref_date)
        
    # Test end date before start date
    with pytest.raises(ValueError, match="cannot be before start date"):
        validate_and_clamp_date_range("2026-06-26", "2026-06-25", current_date=ref_date)
        
    # Test range clamping (> 7 days)
    # Range from 2026-06-26 to 2026-07-04 is 9 days (needs clamping to 7 days, so ends 2026-07-02)
    start, end, warning = validate_and_clamp_date_range("2026-06-26", "2026-07-04", current_date=ref_date)
    assert start == date(2026, 6, 26)
    assert end == date(2026, 7, 2)
    assert warning is not None
    assert "Clamped range to 7 days" in warning
