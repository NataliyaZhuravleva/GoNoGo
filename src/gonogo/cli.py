# © 2026 Nataliya Zhuravleva. All rights reserved.
import argparse
import sys
from datetime import date, timedelta
from typing import List

from gonogo.core import RegionForecast, fetch_conditions, validate_and_clamp_date_range

# ANSI Escape Colors
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_RESET = "\033[0m"

def get_color_ansi(color_name: str, enabled: bool = True) -> str:
    """Get the ANSI color escape code."""
    if not enabled:
        return ""
    if color_name == "Green":
        return COLOR_GREEN
    elif color_name == "Yellow":
        return COLOR_YELLOW
    elif color_name == "Red":
        return COLOR_RED
    return ""

def format_color_badge(color_name: str, enabled: bool = True) -> str:
    """Format a single character color badge (e.g. G, Y, R) with color coding."""
    char = color_name[0]  # 'G', 'Y', or 'R'
    ansi = get_color_ansi(color_name, enabled)
    reset = COLOR_RESET if (enabled and ansi) else ""
    return f"{ansi}[{char}]{reset}"

def format_color_block(color_name: str, enabled: bool = True) -> str:
    """Format a colored block symbol (■) or character (G/Y/R) for day-parts."""
    if not enabled:
        return color_name[0]  # 'G', 'Y', or 'R'
    ansi = get_color_ansi(color_name, enabled)
    reset = COLOR_RESET if (enabled and ansi) else ""
    return f"{ansi}■{reset}"

def display_board(forecasts: List[RegionForecast], start_date: date, end_date: date, use_color: bool = True):
    """Print the conditions board to stdout."""
    border = "=" * 85
    print(border)
    print(f"                       GoNoGo PNW CONDITIONS BOARD")
    print(f"             Forecast Range: {start_date} to {end_date}")
    print(border)
    print()

    # Get the list of dates to print headers
    date_list: List[str] = []
    for f in forecasts[0].tiers["peak"].forecast_days:
        # Just format as MM/DD
        date_list.append(f.date[5:])  # slice off 'YYYY-'

    for idx, reg in enumerate(forecasts, start=1):
        print(f"{idx:2d}. {reg.region_name} (Headline: {reg.headline_peak_name})")
        print(f"    Past 48h Precipitation: {reg.past_48h_precip_mm:.1f} mm")
        print("    " + "-" * 77)
        # Dynamic headers depending on number of days
        headers = ["Tier", "Elevation", "Worst"]
        for d_str in date_list:
            headers.append(f"  {d_str} (M D E)")
            
        header_line = f"    {headers[0]:<6} {headers[1]:<10} {headers[2]:<6}"
        for h in headers[3:]:
            header_line += f" {h:<13}"
        print(header_line)
        print("    " + "-" * 77)

        for tier_key in ["base", "mid", "peak"]:
            tier = reg.tiers[tier_key]
            
            # Format row
            worst_badge = format_color_badge(tier.composite_color, use_color)
            row = f"    {tier.tier_name:<6} {f'{int(tier.elevation_ft)} ft':<10}  {worst_badge:<4} "
            
            for day in tier.forecast_days:
                m_block = format_color_block(day.parts.morning["composite_color"], use_color)
                d_block = format_color_block(day.parts.midday["composite_color"], use_color)
                e_block = format_color_block(day.parts.evening["composite_color"], use_color)
                row += f"   {m_block} {d_block} {e_block}       "
                
            print(row)
            
        print("    " + "-" * 77)
        print()

def main():
    parser = argparse.ArgumentParser(description="GoNoGo Mountaineering Conditions Board CLI")
    parser.add_argument(
        "--date",
        type=str,
        help="Target start date (YYYY-MM-DD). Defaults to tomorrow."
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="Optional target end date (YYYY-MM-DD) for a custom range."
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in output."
    )
    
    args = parser.parse_args()
    
    # Calculate tomorrow as default start date
    today = date.today()
    default_start_str = (today + timedelta(days=1)).isoformat()  # tomorrow
    
    start_str = args.date or default_start_str
    
    try:
        start_date, end_date, warning = validate_and_clamp_date_range(
            start_date_str=start_str,
            end_date_str=args.end_date,
            current_date=today
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
        
    if warning:
        # Print warning in yellow color if enabled
        ansi_yellow = COLOR_YELLOW if not args.no_color else ""
        ansi_reset = COLOR_RESET if not args.no_color else ""
        print(f"{ansi_yellow}Warning: {warning}{ansi_reset}\n", file=sys.stderr)

    try:
        forecasts = fetch_conditions(start_date, end_date)
    except Exception as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        sys.exit(1)

    display_board(forecasts, start_date, end_date, use_color=not args.no_color)

if __name__ == "__main__":
    main()
