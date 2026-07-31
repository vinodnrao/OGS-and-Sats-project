# Other programs in the same directory
from tle_fetch   import fetch_tle # Part 1 - Fetching TLE Data
from coordinates import GEODETIC_to_ECEF # Part 2 - Constructing co-ordinate systems from the OGS location(s)
from passes import find_passes # Part 3 - Calculating when the satellites are passing over the OGS location(s)
from solar_position import sun_position_eci, shadow_status, solar_elevation

from datetime import datetime, timezone, timedelta

OGS_LOCATIONS = {"York": (53.94762420654297,-1.026491403579712, 0.017)} # dict mapping for co-ordinates from the OGS tuple
# lat, lon, alt-km
# "Oxford": (51.7594, -1.2637, 0.065)
# Satellite ID's
SATELLITES = {"SPOQC":68423}
#"SPEQTRE": 66769
SCAN_START     = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc) # Today
SCAN_DAYS      = 30 # Scanning over a month timeframe
MIN_ELEVATION = [30]   # threshold of elevation, allows for multiple minimums
MAX_ELEVATION = 150
DIRECTION_FILTER="both"

def main():
    # Compute the OGS's ECEF positions
    ogs_positions = {name: GEODETIC_to_ECEF(*coords) for name, coords in OGS_LOCATIONS.items()}

    # Fetch the TLE's for all the satellites
    print("\nFetching TLEs...")
    known_sats = {k: v for k, v in SATELLITES.items() if v is not None}
    sats_raw = fetch_tle(known_sats)
    sats={name: data['sat'] for name, data in sats_raw.items()}

    # Run pass finder for each OGS × satellite × elevation threshold
    print("\nScanning passes...\n")
    for ogs_name, ogs_ecef in ogs_positions.items():
        lat, lon, h=OGS_LOCATIONS[ogs_name]
        for sat_name, sat in sats.items():
            print(f"-- {sat_name} over {ogs_name} --")
            # debug_eclipse(sats["SPOQC"],SCAN_START)
            for min_el in MIN_ELEVATION:
                passes = find_passes(sat=sat,ogs_ecef=ogs_ecef,start_utc=SCAN_START,ogs_lat=lat,ogs_lon=lon,hours=SCAN_DAYS*24,min_el=min_el,max_el=MAX_ELEVATION)
                print(f"  El > {min_el:2d}':  {len(passes)} passes over {SCAN_DAYS} days")

            # Filtering passes that fit into our 60 degree elevation
            passes_60 = find_passes(sat, ogs_ecef, SCAN_START,ogs_lat=lat,ogs_lon=lon, hours=SCAN_DAYS*24, min_el=MIN_ELEVATION[0], max_el=MAX_ELEVATION)
            
            # Table to display the pass information
            if passes_60:
                print(f"\n  Passes above {MIN_ELEVATION}°-{MAX_ELEVATION}°:")
                print(f"  {'ID':<6} {'Rise (UTC)':<27} {'Max El':>3} {'Az':>6} {'Dir':>5} {'Duration':>10} {'Shadow':>9} {'Solar_el':>9} {'Usable':>9}")
                print(f"  {'-'*95}")
                usable_count=0
                for idx, p in enumerate(passes_60, start=1):
                    direction = "S" if p['max_az'] >= 180 else "N"
                    if DIRECTION_FILTER != "both" and direction != DIRECTION_FILTER:
                        continue
                    pass_id=f"{sat_name[:3].upper()}-{idx:03d}"
                    shadow = p.get('shadow') or 'Unknown'
                    solar_el = f"{p['solar_el']:.1f}°" if p.get('solar_el') is not None else "N/A"
                    is_usable=(shadow=='sunlit' and p.get('solar_el') is not None and p['solar_el']<-12.0)
                    usable_string="YES" if is_usable else "NO"
                    if is_usable:
                        usable_count+=1

                    print(f"{pass_id:<8} "
                          f"{str(p['rise']):<27} "
                          f"{p['max_el']:>6.1f}° "
                          f"{p['max_az']:>5.1f}° "
                          f"{direction:>5} "
                          f"{p['duration']:>7}s "
                          f"{shadow:>10} "
                          f"{solar_el:>8} "
                          f"{usable_string:>7}")
                print(f"Usable Passes (Sunlit+Dark OGS): {usable_count} / {len(passes_60)}\n")

# Stops it being ran outside of this main file
if __name__ == "__main__":
    main()
