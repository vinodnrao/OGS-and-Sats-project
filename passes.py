from datetime import timedelta, datetime, timezone
from propagator import elevation_angle
from solar_position import sun_position_eci, in_eclipse, solar_elevation
from sgp4.api import jday
import numpy as np

def refined_time(sat, ogs_ecef, ogs_lat, ogs_lon, t_delta, min_el, max_el, crossing='rise'):
    # Narrow down a pass time to 1s accuracy
    # looking for crossing='rise' where el passes MAX_ELEVATION upward or crossing='set' where el passes MIN_ELEVATION downward
    step=timedelta(seconds=1)
    t=t_delta-timedelta(seconds=10)
    el_u=None

    for _ in range(25):
        result=elevation_angle(sat, ogs_ecef, t, ogs_lat, ogs_lon)
        if result:
            el=result[0]
            if el_u is not None:
                if crossing=='rise' and el_u<min_el<=el:
                    return t
                if crossing=='set' and el_u>=min_el>el:
                    return t
            el_u=el
        t+=step
    return t_delta # In case narrowing it down does not work

def find_passes(sat, ogs_ecef,start_utc, ogs_lat, ogs_lon,hours=24, min_el=60.0, max_el=90, step_secs=10):
    passes, in_pass=[], False
    current_pass={}
    t=start_utc
    end_time=start_utc+timedelta(hours=hours)

    while t<end_time:
        result=elevation_angle(sat,ogs_ecef,t,ogs_lat,ogs_lon)

        if result:
            el,az,rng=result
            # Elevation within the window
            in_window=min_el<el<max_el

            if in_window and not in_pass:
                # The pass starts
                in_pass=True
                # Narrowing it down to second accuracy
                rise_refined=refined_time(sat,ogs_ecef,ogs_lat,ogs_lon,t,min_el,max_el,crossing='rise')
                current_pass={'rise': rise_refined, 'max_el': el, 'max_az': az}
            elif in_window and in_pass:
                # Still in the pass
                if el>current_pass['max_el']:
                    current_pass['max_el']=el
                    current_pass['max_az']=az

                    # Eclipse and sun position at the new maximum
                    yr, mo, dy = t.year, t.month, t.day
                    hr, mn, sc = t.hour, t.minute, t.second + t.microsecond/1e6
                    jd, fr = jday(yr, mo, dy, hr, mn, sc)
                    jd_full = jd + fr

                    # Satellite ECI position for Eclipse check
                    e, r_sat,_= sat.sgp4(jd,fr)
                    if e==0:
                        r_sun=sun_position_eci(jd_full)
                        current_pass['eclipse']=in_eclipse(np.array(r_sat),r_sun)
                        current_pass['solar_el']=solar_elevation(r_sun,ogs_ecef,jd_full,ogs_lat,ogs_lon)
            elif not in_window and in_pass:
                # Pass ends
                in_pass=False
                # Narrow down accuracy
                set_refined=refined_time(sat,ogs_ecef,ogs_lat,ogs_lon,t,min_el,max_el,crossing='set')
                current_pass['set']=set_refined
                current_pass['duration']=(set_refined-current_pass['rise']).seconds

                # Updating eclipse and sun elevation if not updated
                current_pass.setdefault('eclipse',None)
                current_pass.setdefault('solar_el',None)

                passes.append(current_pass)
                current_pass={}

            t += timedelta(seconds=step_secs)
    return passes