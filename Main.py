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
SATELLITES = {"SPEQTRE": 66769}
# "SPOQC":68423
# "SPEQTRE": 66769
SCAN_START     = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc) # Today
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
                print(f"\n  {sat_name} over {ogs_name} - passes {MIN_ELEVATION[0]}°-{MAX_ELEVATION}°:")
                print()
                print(f"  {'ID':<6} {'Rise (UTC)':<32} {'Day/Night':<10} {'Max El':>7} {'Az':>7} {'Dir':>5} {'Duration':>9} {'Shadow':>10} {'Solar_el':>9} {'Usable':>7}   {'Reason':<28}")
                print(f"  {'-'*138}")
                usable_count=0
                for idx, p in enumerate(passes_60, start=1):
                    direction = "S" if p['max_az'] >= 180 else "N"
                    if DIRECTION_FILTER != "both" and direction != DIRECTION_FILTER:
                        continue
                    pass_id=f"{sat_name[:3].upper()}-{idx:03d}"

                    solar_el_val = p.get('solar_el')
                    is_night = solar_el_val is not None and solar_el_val < 0.0
                    day_night = "Night" if is_night else "Day"

                    if is_night:
                        shadow_display="N/A"
                        is_usable=solar_el_val<0.0
                    else:
                        shadow_display=p.get('shadow') or 'Unknown'
                        is_usable=False

                    solar_el_display = f"{solar_el_val:.1f}°" if solar_el_val is not None else "N/A"
                    usable_string="YES" if is_usable else "NO"
                    if is_usable:
                        usable_count += 1

                    if is_usable:
                        reason=""
                    else:
                        reasons=[]
                        if not is_night:
                            if solar_el_val is not None:
                                reasons.append(f"daytime(sol={solar_el_val:.1f}')")
                            else:
                                reasons.append("daytime")
                        elif solar_el_val is not None and solar_el_val >= 0.0:
                            reasons.append(f"twilight({solar_el_val:.1f}')")

                        shadow_val=p.get('shadow')
                        if not is_night and shadow_val and shadow_val != 'sunlit':
                            reasons.append(f"sat={shadow_val}")

                        reason=", ".join(reasons) if reasons else "unknown"

                    print(f"{pass_id:<9} "
                          f"{str(p['rise']):<32} "
                          f"{day_night:<10} "
                          f"{p['max_el']:>6.1f}° "
                          f"{p['max_az']:>6.1f}° "
                          f"{direction:>5} "
                          f"{p['duration']:>7}s "
                          f"{shadow_display:>10}"
                          f"{solar_el_display:>9}"
                          f"{usable_string:>7}   "
                          f"{reason:<28}")
                print(f"\n {'-'*138}")
                print(f"Usable Passes: {usable_count} / {len(passes_60)}\n")

# Stops it being ran outside of this main file
if __name__ == "__main__":
    main()
