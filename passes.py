
from datetime import timedelta, datetime, timezone
from propagator import elevation_angle
from solar_position import sun_position_eci, shadow_status, solar_elevation
from sgp4.api import jday
import numpy as np


def refined_time(sat, ogs_ecef, ogs_lat, ogs_lon, t_delta,min_el, max_el, crossing='rise'):
    """Narrow down a pass rise or set time to 1-second accuracy."""
    step = timedelta(seconds=1)
    t    = t_delta - timedelta(seconds=10)
    el_u = None

    for _ in range(25):
        result = elevation_angle(sat, ogs_ecef, t, ogs_lat, ogs_lon)
        if result:
            el = result[0]
            if el_u is not None:
                if crossing == 'rise' and el_u < min_el <= el:
                    return t
                if crossing == 'set'  and el_u >= min_el > el:
                    return t
            el_u = el
        t += step
    return t_delta  # fallback to coarse time


def compute_eclipse_fields(sat, ogs_ecef, ogs_lat, ogs_lon, t):
    yr, mo, dy = t.year, t.month, t.day
    hr, mn, sc = t.hour, t.minute, t.second + t.microsecond / 1e6

    # Split form — jd is integer part, fr is fractional day
    # SGP4 requires these separate to preserve floating point precision
    jd, fr  = jday(yr, mo, dy, hr, mn, sc)
    jd_full = jd + fr   # combined only for sun position and gmst

    # SGP4 propagation using split form
    e, r_sat, _ = sat.sgp4(jd, fr)
    if e != 0:
        return None, None

    # Sun position uses the full Julian Date
    r_sun  = sun_position_eci(jd_full)
    shadow    = shadow_status(np.array(r_sat), r_sun)
    sol_el = solar_elevation(r_sun, ogs_ecef, jd_full, ogs_lat, ogs_lon)
    return shadow, sol_el


def find_passes(sat, ogs_ecef, start_utc, ogs_lat, ogs_lon,hours=24, min_el=60.0, max_el=90.0, step_secs=10):
    passes       = []
    in_pass      = False
    current_pass = {}
    t            = start_utc
    end_time     = start_utc + timedelta(hours=hours)

    while t < end_time:
        result = elevation_angle(sat, ogs_ecef, t, ogs_lat, ogs_lon)

        if result:
            el, az, rng = result
            in_window   = min_el < el < max_el

            if in_window and not in_pass:
                # Pass starts
                in_pass = True
                try:
                    rise_refined = refined_time(
                        sat, ogs_ecef, ogs_lat, ogs_lon,
                        t, min_el, max_el, crossing='rise')
                except Exception:
                    rise_refined = t

                # Compute shadow at pass start immediately
                # so it is never None even for single-step passes
                shadow, sol_el = compute_eclipse_fields(sat, ogs_ecef, ogs_lat, ogs_lon, t)

                current_pass = {
                    'rise':     rise_refined,
                    'max_el':   el,
                    'max_az':   az,
                    'set':      None,
                    'duration': None,
                    'shadow':  shadow, # sunlit / penumbra / umbra
                    'solar_el': sol_el,
                }

            elif in_window and in_pass:
                # ── Still in pass — update maximum ──
                if el > current_pass['max_el']:
                    current_pass['max_el'] = el
                    current_pass['max_az'] = az

                    # Recompute eclipse at the new maximum elevation
                    # This is the most operationally relevant moment
                    shadow, sol_el = compute_eclipse_fields(sat, ogs_ecef, ogs_lat, ogs_lon, t)
                    if shadow is not None:
                        current_pass['shadow']  = shadow
                        current_pass['solar_el'] = sol_el

            elif not in_window and in_pass:
                # ── Pass ends ──
                in_pass = False
                try:
                    set_refined = refined_time(
                        sat, ogs_ecef, ogs_lat, ogs_lon,
                        t, min_el, max_el, crossing='set')
                except Exception:
                    set_refined = t

                current_pass['set']= set_refined
                current_pass['duration'] = (set_refined-current_pass['rise']).seconds

                passes.append(current_pass)
                current_pass = {}

        # ── Always advance time — outside the if result block ──
        t += timedelta(seconds=step_secs)

    return passes
