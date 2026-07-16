from sgp4.api import Satrec, jday
from coordinates import ECEF_to_ECI, gmst
import numpy as np

def elevation_angle(sat, ogs_ecef, dt, ogs_lat, ogs_lon):
    # Taking a satellite object from tle_fetch, the OGS ECEF position vector from coordinates, and a UTC date time
    # Will return elevation angle in degrees and slant range in km

    yr, mo, dy=dt.year, dt.month, dt.day
    hr, mn, sc=dt.hour, dt.minute, dt.second +dt.microsecond/1e6
    jd, fr=jday(yr, mo, dy, hr, mn, sc)

    e, r_ECI, v_ECI=sat.sgp4(jd,fr)
    if e!=0:
        return None # Propagation error
    
    # This will convert our OGS to ECI at this moment
    theta=gmst(jd+fr)
    ogs_ECI=ECEF_to_ECI(ogs_ecef, theta)

    # Topocentric range vector (in ECI)
    rho_ECI=np.array(r_ECI)-ogs_ECI

    # Rotate range vector in local frame at OGS
    phi=np.radians(ogs_lat) # lat
    lam=np.radians(ogs_lon) # lon
    sin_phi, cos_phi=np.sin(phi), np.cos(phi)
    sin_lam, cos_lam=np.sin(lam), np.cos(lam)

    # South, East, Zenith rotation
    rho_ECEF=ECEF_to_ECI(rho_ECI, -theta) # Converting to ECEF into South, East, Zenith
    S=(sin_phi*cos_lam*rho_ECEF[0]+sin_phi*sin_lam*rho_ECEF[1]-cos_phi*rho_ECEF[2])
    E=(-sin_lam*rho_ECEF[0]+cos_lam*rho_ECEF[1])
    Z=(cos_phi*cos_lam*rho_ECEF[0]+cos_phi*sin_lam*rho_ECEF[1]+sin_phi*rho_ECEF[2])

    rng=np.sqrt(S**2+E**2+Z**2)
    el=np.degrees(np.arcsin(Z/rng))
    az=np.degrees(np.arctan2(E, -S)) % 360
    return el, az, rng