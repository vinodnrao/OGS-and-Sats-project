from datetime import timedelta

def find_pass_pairs(passes_a, passes_b, label_a, label_b, max_gap_hours=12):
    """Find all pass pairs for two OGS's for the same satellite and computes the time between them for max communication"""

    """Pair is valid if:
    - both passes are individually usable (usable=YES)
    - the gap between them is less than_max_gap_hours
    - either Vigo then York or York then Vigo"""

    pairs=[]

    usable_a=[p for p in passes_a if _is_usable(p)]
    usable_b=[p for p in passes_b if _is_usable(p)]

    for pa in usable_a:
        for pb in usable_b:
            # determine which pass is first
            if pa['rise'] < pb['rise']:
                first, second= pa, pb
                first_label, second_label=label_a, label_b
            else:
                first, second=pb, pa
                first_label, second_label=label_b, label_a

            # Gap between both passes
            gap=second['rise']-first['set']

            if timedelta(0)<gap<timedelta(hours=max_gap_hours):
                pairs.append({'first_ogs': first_label,
                              'first_rise': first['rise'],
                              'first_set': first['set'],
                              'second_ogs': second_label, 
                              'second_rise': second['rise'], 
                              'second_set': second['set'], 
                              'gap_minutes': gap.total_seconds()/60,
                              'gap_seconds': gap.total_seconds(),
                              'first_max_el': first['max_el'], 
                              'second_max_el': second['max_el'], 
                              })

    # sorting by shortest gap
    pairs.sort(key=lambda x: x['gap_minutes'])
    return pairs

def _is_usable(p):
    """checking if a pass meets the usable criteria"""
    solar_el=p.get('solar_el')
    is_night=solar_el is not None and solar_el < 0.0
    shadow = p.get('shadow')
    if is_night:
        return True
    return False # for daytime passes
