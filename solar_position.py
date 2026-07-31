import numpy as np
from coordinates import ECEF_to_ECI, gmst, ECI_to_ECEF

def sun_position_eci(jd):
    # Low precision solar position in ECI (km)
    # Days from J2000
    n    = jd - 2451545.0 
    # Mean longitude in degrees                      
    L    = (280.460 + 0.9856474 * n) % 360      
    # Mean anomaly in radians
    g    = np.radians((357.528 + 0.9856003 * n) % 360)
    # Ecliptic longitude
    lam  = np.radians(L + 1.915 * np.sin(g) + 0.020 * np.sin(2*g))
    # Angle between Earths rotation axis and it's orbital plane
    eps  = np.radians(23.439 - 0.0000004 * n) 

    # Distance in AU then convert to km
    R_AU = 1.00014 - 0.01671*np.cos(g) - 0.00014*np.cos(2*g)
    R_km = R_AU * 149597870.7

    # ECI components
    x_sun =  R_km * np.cos(lam)
    y_sun =  R_km * np.cos(eps) * np.sin(lam)
    z_sun =  R_km * np.sin(eps) * np.sin(lam)
    return np.array([x_sun, y_sun, z_sun])

def shadow_status(r_sat, r_sun):
    # Returns 'umbra', 'penumbra', or 'sunlit'.
    # Umbra   = full shadow, satellite completely blocked from Sun.
    # Penumbra = partial shadow, satellite partially blocked.
    # Sunlit   = full sunlight.

    R_earth   = 6371.0
    R_sun     = 696000.0
    r_sun_norm = np.linalg.norm(r_sun)
    sun_hat    = r_sun / r_sun_norm
    sat_dot_sun = np.dot(r_sat, sun_hat)

    # Satellite on sunlit side — cannot be in any shadow
    if sat_dot_sun > 0:
        return 'sunlit'

    d    = -sat_dot_sun
    perp = np.linalg.norm(r_sat - sat_dot_sun * sun_hat)

    # Umbra cone radius — narrows away from Earth
    r_umbra=R_earth-(R_sun-R_earth)*d /r_sun_norm

    # Penumbra cone radius — widens away from Earth
    r_penumbra = R_earth + (R_sun + R_earth) * d / r_sun_norm

    if perp < r_umbra:
        return 'umbra'
    elif perp < r_penumbra:
        return 'penumbra'
    else:
        return 'sunlit'


def solar_elevation(r_sun, ogs_ecef, jd_fr, ogs_lat, ogs_lon):
    theta    = gmst(jd_fr)
    ogs_eci  = ECEF_to_ECI(ogs_ecef, theta)
    
    rho_sun  = r_sun - ogs_eci
    rho_ecef=ECI_to_ECEF(rho_sun,theta)
    
    phi     = np.radians(ogs_lat)
    lam     = np.radians(ogs_lon)
    sin_phi, cos_phi = np.sin(phi), np.cos(phi)
    sin_lam, cos_lam = np.sin(lam), np.cos(lam)

    Z = (cos_phi*cos_lam*rho_ecef[0]
       + cos_phi*sin_lam*rho_ecef[1]
       + sin_phi*rho_ecef[2])
    rng = np.linalg.norm(rho_ecef)
    return np.degrees(np.arcsin(Z / rng))
