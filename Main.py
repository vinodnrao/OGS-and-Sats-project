# All programs in the same directory
# Config file (for OGS's & Satellites) also in the same directory
from tle_fetch   import fetch_tle # Part 1 - Fetching TLE Data
from coordinates import GEODETIC_to_ECEF # Part 2 - Constructing co-ordinate systems from the OGS location(s)
from passes import find_passes # Part 3 - Calculating when the satellites are passing over the OGS location(s)
from solar_position import sun_position_eci, shadow_status, solar_elevation # Part 4 - Calculating shadow angles and sun position
from network import find_pass_pairs # Part 5 - Computing concurrent passes between OGS's that could link together
from mapping import save_passes_txt, save_pairs_txt # Part 6 - Saving the data as CSV files

from datetime import datetime, timezone, timedelta
import numpy as np
import openpyxl

# CONFIG
# OGS_LOCATIONS = {"York": (53.94762420654297,-1.026491403579712, 0.017),"VIGO": (42.1724,  -8.6883,  0.050)} # dict mapping for co-ordinates from the OGS tuple
# SATELLITES = {"SPOQC":68423}

def load_config(filepath='OGS_Config.xlsx'):
    # Read the OGS Location co-ordinates and satellite NORAD ID's from the .xlsx file
    # Row 1 is the header
    workbook=openpyxl.load_workbook(filepath, data_only=True)
    # Read OGS
    OGS_sheet=workbook['OGS_Input']
    OGS_locations={}
    for row in OGS_sheet.iter_rows(min_row=2, values_only=True):
        name, lat, lon, alt = row[0], row[1], row[2], row[3]
        # Stop at empty row
        if name is None:
            break
        OGS_locations[str(name).strip()]=(float(lat), float(lon), float(alt))
    # Read Satellites
    SAT_sheet=workbook['Satellite_Input']
    Satellites={}
    for row in SAT_sheet.iter_rows(min_row=2, values_only=True):
        name, norad_ID= row[0], row[1]
        if name is None:
            break
        Satellites[str(name).strip()]=int(norad_ID)
    workbook.close()

    # Confirming load
    print("Config loaded from xlsx:")
    print(f"OGS: {list(OGS_locations.keys())}")
    print(f"Satellites {list(Satellites.keys())}")
    return OGS_locations, Satellites

# CONFIG
OGS_LOCATIONS, SATELLITES = load_config('OGS_Config.xlsx')
SCAN_START     = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc) # Today
SCAN_DAYS      = 30 # Scanning over a month timeframe
MIN_ELEVATION = [30]   # threshold of elevation, allows for multiple minimums
MAX_ELEVATION = 150
DIRECTION_FILTER="both"
SOLAR_EXCLUSION_DEG=10.0

def get_OGS_pairs(ogs_locations):
    # Returns the OGS Names from the locations dict
    names=list(ogs_locations.keys())
    pairs=[]
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            pairs.append((names[i], names[j]))
    return pairs

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

    all_passes={}

    for ogs_name, ogs_ecef in ogs_positions.items():
        lat, lon, h=OGS_LOCATIONS[ogs_name]
        for sat_name, sat in sats.items():

            sat_data=sats_raw.get(sat_name)
            if sat_data is None:
                print(f"[SKIP] {sat_name} - no valid TLE loaded")
                continue
            no_kozai=sat_data['sat'].no_kozai
            if no_kozai==0.0:
                print(f"[SKIP] {sat_name} - mean motion is zero, cannot complete orbital period")
                continue

            orbital_period_min=(2*np.pi)/no_kozai # minutes per orbit

            print(f"-- {sat_name} over {ogs_name} --")

            passes_60 = find_passes(sat=sat,ogs_ecef=ogs_ecef,start_utc=SCAN_START,ogs_lat=lat,ogs_lon=lon,hours=SCAN_DAYS*24,min_el=MIN_ELEVATION[0],max_el=MAX_ELEVATION)

            all_passes[(sat_name, ogs_name)]=passes_60

            print(f"  El > {MIN_ELEVATION[0]:2d}':  {len(passes_60)} passes over {SCAN_DAYS} days")
            
            # Table to display the pass information
            if passes_60:
                print(f"\n  {sat_name} over {ogs_name} - passes {MIN_ELEVATION[0]}°-{MAX_ELEVATION}°:")
                print()
                print(f"  {'ID':<6} {'Rise (UTC)':<32} {'Day/Night':<10} {'Max El':>7} {'Az':>7} {'Dir':>5} {'Duration':>9} {'Shadow':>10} {'Solar_el':>9} {'Sun Sep':>8} {'Usable':>7}   {'Reason':<28}")
                print(f"  {'-'*152}")
                usable_count=0
                for idx, p in enumerate(passes_60, start=1):
                    direction = "S" if p['max_az'] >= 180 else "N"
                    if DIRECTION_FILTER != "both" and direction != DIRECTION_FILTER:
                        continue
                    pass_id=f"{sat_name[:3].upper()}-{idx:03d}"

                    solar_el_val = p.get('solar_el')
                    min_solar_val=p.get('min_solar_sep', 180.0)
                    is_night = solar_el_val is not None and solar_el_val < 0.0
                    min_solar_sep=p.get('min_solar_sep', 180.0)
                    day_night = "Night" if is_night else "Day"

                    if is_night:
                        shadow_display="N/A"
                        is_usable=True
                        reason=""
                    else:
                        shadow_display=p.get('shadow') or 'Unknown'
                        # Daytime: usable only if Sun is never within the exclusion cone
                        sun_in_path=min_solar_sep<SOLAR_EXCLUSION_DEG
                        is_usable=not sun_in_path
                        if is_usable:
                            reaon=f"day-ok(sun_sep={min_solar_sep:.1f}')"
                        else:
                            reason=(f"sun_in_path({min_solar_sep:.1f})'<{SOLAR_EXCLUSION_DEG}')"
                                    if solar_el_val is not None
                                    else "daytime")

                    solar_el_display = f"{solar_el_val:.1f}°" if solar_el_val is not None else "N/A"
                    min_sep_display= (f"{min_solar_sep:.1f}'"
                                      if min_solar_sep<180.0 else "N/A")
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
                          f"{min_sep_display:>8}"
                          f"{usable_string:>7}   "
                          f"{reason:<35}")
                print(f"\n {'-'*152}")
                print(f"Usable Passes: {usable_count} / {len(passes_60)}\n")

    for sat_name in sats:

        for ogs_a, ogs_b in get_OGS_pairs(OGS_LOCATIONS):
            passes_a=all_passes.get((sat_name, ogs_a),[])
            passes_b=all_passes.get((sat_name, ogs_b),[])

            print(f"\n [pairing] {sat_name}: {ogs_a}={len(passes_a)}, {ogs_b}={len(passes_b)}")
            if not passes_a or not passes_b:
                print(f" [pairing] Skipping - no passes for one or both OGS Locations")
                print(f" [pairing] Available Keys: {list(all_passes.keys())}")
                continue

            simultaneous, sequential =find_pass_pairs(passes_a, passes_b, ogs_a, ogs_b, orbital_period_min=orbital_period_min)
            all_pairs = simultaneous + sequential

            if all_pairs:
                print(f"\n  {'='*175}")
                print(f"  {sat_name} relay: {ogs_a} <> {ogs_b}   "
                    f"Simultaneous: {len(simultaneous)}   "
                    f"Sequential: {len(sequential)}")
                print(f"  {'='*190}\n")

                print(f"  {'#':<4} "
                    f"{'OGS 1':<8} {'Rise 1':<28} {'Dur':>6} {'El':>6} {'Shadow':>8} {'SunSep':>11}   "
                    f"{'OGS 2':<8} {'Rise 2':<28} {'Dur':>6} {'El':>6} {'Shadow':>8} {'SunSep':>11}   "
                    f"{'Pass':>6}   {'Gap/Overlap':>12}")
                print(f"  {'-'*190}")

                for i, pair in enumerate(all_pairs[:20], start=1):
                    fd_s   = int((pair['first_set']  - pair['first_rise']).total_seconds())
                    sd_s   = int((pair['second_set'] - pair['second_rise']).total_seconds())
                    fd_str = f"{fd_s//60}m {fd_s%60}s"
                    sd_str = f"{sd_s//60}m {sd_s%60}s"

                    # Gap or overlap depending on type
                    if pair['overlap_seconds'] > 0:
                        ov      = int(pair['overlap_seconds'])
                        go_str  = f"+{ov//60}m {ov%60}s"   # + prefix = overlap
                    else:
                        gap_s   = int(pair['gap_seconds'])
                        go_str  = (f"{gap_s//3600}h {(gap_s%3600)//60}m {gap_s%60}s"
                                if gap_s >= 3600
                                else f"{gap_s//60}m {gap_s%60}s")

                    # Shadow at max elevation — pulled from pass dict if available
                    f_shadow = pair.get('first_shadow', 'N/A')   # night passes — shadow not relevant
                    s_shadow = pair.get('second_shadow', 'N/A')

                    # Solar separation
                    f_sun_sep = pair.get('first_sun_sep', 180.0)
                    s_sun_sep = pair.get('second_sun_sep', 180.0)
                    f_sep_str= f"{f_sun_sep:.1f}'" if f_sun_sep<180.0 else "N/A"
                    s_sep_str= f"{s_sun_sep:.1f}'" if s_sun_sep<180.0 else "N/A"

                    print(f"  {i:<4} "
                        f"{pair['first_ogs']:<8} "
                        f"{str(pair['first_rise']):<28} "
                        f"{fd_str:>6} "
                        f"{pair['first_max_el']:>5.1f}°  "
                        f"{f_shadow:>8}   "
                        f"{f_sep_str:>7}    "
                        f"{pair['second_ogs']:<8} "
                        f"{str(pair['second_rise']):<28} "
                        f"{sd_str:>6} "
                        f"{pair['second_max_el']:>5.1f}°  "
                        f"{s_shadow:>8}   "
                        f"{s_sep_str:>7}    "
                        f"{pair['orbit_label']:>6}   "
                        f"{go_str:>12}")

                print(f"\n  {'-'*175}")
                if simultaneous:
                    best = simultaneous[0]
                    ov   = int(best['overlap_seconds'])
                    print(f"  Best simultaneous (P+{best['n_orbits']}): "
                        f"{ov//60}m {ov%60}s shared — "
                        f"{str(best['first_rise'])[:16]}")
                if sequential:
                    best  = sequential[0]
                    gap_s = int(best['gap_seconds'])
                    print(f"  Best sequential (P+{best['n_orbits']}): "
                        f"{best['first_ogs']} → {best['second_ogs']} — "
                        f"gap {gap_s//60}m {gap_s%60}s")
                print(f"  {'='*175}\n")
                save_pairs_txt(simultaneous, sequential, sat_name, ogs_a, ogs_b)

            else:
                print(f"  No relay opportunities found within {12}h threshold.\n")

    for(sat_name, ogs_name), passes in all_passes.items():
        lat, lon, _ = OGS_LOCATIONS[ogs_name]
        save_passes_txt(passes, sat_name, ogs_name)

# Stops it being ran outside of this main file
if __name__ == "__main__":
    main()
