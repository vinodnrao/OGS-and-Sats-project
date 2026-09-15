import csv
from datetime import timezone

def save_passes_txt(passes, sat_name, ogs_name, filename=None):
    """Save individual OGS pass list as a CSV file."""
    if filename is None:
        safe_ogs = ogs_name.replace(" ", "_").replace("(", "").replace(")", "")
        filename = f"{sat_name}_{safe_ogs}_passes.csv"

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header row
        writer.writerow(['Rise (UTC)', 'Max El (deg)', 'Az (deg)', 'Dir','Duration (s)', 'Shadow', 'Solar El (deg)', 'Min Solar Sep (deg)', 'Usable'])

        for p in passes:
            direction    = "S" if p['max_az'] >= 180 else "N"
            solar_el_val = p.get('solar_el')
            is_night     = solar_el_val is not None and solar_el_val < 0.0
            shadow       = "N/A" if is_night else (p.get('shadow') or 'unknown')
            solar_str = f"{solar_el_val:.2f}" if solar_el_val is not None else ""
            usable       = "YES" if is_night else "NO"
            min_sep= p.get('min_solar_sep', '')
            min_sep_str= f"{min_sep:.2f}" if isinstance(min_sep, float) and min_sep<180.0 else ""

            writer.writerow([
                str(p['rise']),
                f"{p['max_el']:.2f}",
                f"{p['max_az']:.2f}",
                direction,
                p['duration'],
                shadow,
                solar_str,
                min_sep_str,
                usable
            ])

    print(f"  Saved: {filename}")
    return filename

def save_pairs_txt(simultaneous, sequential, sat_name, ogs_a, ogs_b, filename=None):
    """Save relay pass pairs as a CSV file."""
    if filename is None:
        filename = f"{sat_name}_{ogs_a}_{ogs_b}_pairs.csv"

    all_pairs = simultaneous + sequential

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header row
        writer.writerow([
            'Type',
            f'{ogs_a} Rise (UTC)',
            f'{ogs_a} Set (UTC)',
            f'{ogs_a} Dur (s)',
            f'{ogs_a} Max El (deg)',
            f'{ogs_a} Shadow',
            f'{ogs_a} Min Solar Sep (deg)',
            f'{ogs_b} Rise (UTC)',
            f'{ogs_b} Set (UTC)',
            f'{ogs_b} Dur (s)',
            f'{ogs_b} Max El (deg)',
            f'{ogs_b} Shadow',
            f'{ogs_b} Min Solar Sep (deg)',
            'Pass Offset',
            'Gap (s)',
            'Overlap (s)',
            'Relay Duration (s)'
        ])

        for pair in all_pairs:
            fd_s = int((pair['first_set']  - pair['first_rise']).total_seconds())
            sd_s = int((pair['second_set'] - pair['second_rise']).total_seconds())

            # Type label
            pair_type = 'Simultaneous' if pair['overlap_seconds'] > 0 else 'Sequential'

            f_sep=pair.get('first_sun_sep', '')
            s_sep=pair.get('second_sun_sep', '')
            f_sep_csv = f"{f_sep:.2f}" if isinstance(f_sep, float) and f_sep < 180.0 else ""
            s_sep_csv = f"{s_sep:.2f}" if isinstance(s_sep, float) and s_sep < 180.0 else ""

            writer.writerow([
                pair_type,
                str(pair['first_rise']),
                str(pair['first_set']),
                fd_s,
                f"{pair['first_max_el']:.2f}",
                pair.get('first_shadow', ''),
                f_sep_csv,
                str(pair['second_rise']),
                str(pair['second_set']),
                sd_s,
                f"{pair['second_max_el']:.2f}",
                pair.get('second_shadow', ''),
                s_sep_csv,
                pair['orbit_label'],
                int(pair['gap_seconds']),
                int(pair['overlap_seconds']),
                int(pair['relay_duration'])
            ])

    print(f"  Saved: {filename}")
    return filename
