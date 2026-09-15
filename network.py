from datetime import timedelta
import math

def find_pass_pairs(passes_a, passes_b, label_a, label_b, max_gap_hours=12, orbital_period_min=94.8):

    simultaneous = []
    sequential   = []

    usable_a = [p for p in passes_a if _is_usable(p)]
    usable_b = [p for p in passes_b if _is_usable(p)]

    for pa in usable_a:
        for pb in usable_b:
            if pa['rise'] <= pb['rise']:
                first, second             = pa, pb
                first_label, second_label = label_a, label_b
            else:
                first, second             = pb, pa
                first_label, second_label = label_b, label_a

            gap = second['rise'] - first['set']

            # Orbit offset — how many orbits between the two passes
            diff_min = (second['rise'] - first['rise']).total_seconds() / 60
            n_orbits = round(diff_min / orbital_period_min)

            base = {
                'first_ogs':    first_label,
                'second_ogs':   second_label,
                'first_rise':   first['rise'],
                'first_set':    first['set'],
                'second_rise':  second['rise'],
                'second_set':   second['set'],
                'first_max_el': first['max_el'],
                'second_max_el':second['max_el'],
                'first_shadow': first.get('shadow', 'N/A'),
                'second_shadow': second.get('shadow', 'N/A'),
                'first_solar_el': first.get('solar_el'),
                'second_solar_el': second.get('solar_el'),
                'first_sun_sep': first.get('min_solar_sep', 180.0),
                'second_sun_sep': second.get('min_solar_sep', 180.0),
                'n_orbits':     n_orbits,
                'orbit_label':  f"P+{n_orbits}",
            }

            # Simultaneous
            if gap <= timedelta(0):
                overlap_start = max(first['rise'],  second['rise'])
                overlap_end   = min(first['set'],   second['set'])
                overlap       = overlap_end - overlap_start
                if overlap > timedelta(0):
                    simultaneous.append({**base,
                        'type':            'Simultaneous',
                        'overlap_seconds': overlap.total_seconds(),
                        'gap_seconds':     0,
                        'relay_duration':  (max(first['set'], second['set'])- min(first['rise'], second['rise'])
                        ).total_seconds(),
                    })

            # Sequential
            elif gap < timedelta(hours=max_gap_hours):
                sequential.append({
                    **base,
                    'type':            'Sequential',
                    'overlap_seconds': 0,
                    'gap_seconds':     gap.total_seconds(),
                    'relay_duration':  (
                        second['set'] - first['rise']
                    ).total_seconds(),
                })

    simultaneous.sort(key=lambda x: -x['overlap_seconds'])
    sequential.sort(key=lambda x: x['gap_seconds'])
    return simultaneous, sequential

SOLAR_EXCLUSION_DEG=10.0

def _is_usable(p):
    # A pass is usable if:
    # - Night (solar_el<0) or 
    # - Daytime but Sun is within SOLAR_EXCLUSION_DEG of satellite path
    # and pass has a valid set time

    solar_el = p.get('solar_el')
    min_sun_sep= p.get('min_solar_sep', 180.0)
    has_set=p.get('set') is not None

    if not has_set:
        return False

    is_night = solar_el is not None and solar_el < 0.0
    if is_night:
        return True

    # Daytime - only usable if Sun stays outside exclusion cone
    return min_sun_sep >= SOLAR_EXCLUSION_DEG
