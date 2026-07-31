import numpy as np
from datetime import datetime, timezone

# WSG4 Constants
a=6378.137 # semi-major axis in km
e_2=0.00669437999014 # first eccentricity squared

def GEODETIC_to_ECEF(lat, lon,h):
    # Geodetic (deg, deg, km) to Ecef (km)
    # Converting to radians for future trig functions, phi for geodetic lat, lam for geodetic lon
    phi=np.radians(lat)
    lam=np.radians(lon)
    N=a/np.sqrt(1-e_2*np.sin(phi)**2) # Prime vertical radius of curvature, equals a at the equator
    X=(N+h)*np.cos(phi)*np.cos(lam)
    Y=(N+h)*np.cos(phi)*np.sin(lam)
    Z=(N*(1-e_2)+h)*np.sin(phi)
    return np.array([X,Y,Z])

def gmst(julian_date): # Takes a date and will return the GMST side-real time as an angle in rads
    days_jd=julian_date-2451545 # Days since the J2000 epoch
    cent_jd=days_jd/36525 # Converting those days into centuries
    theta=(280.46061837+(360.98564736629*days_jd)+(0.000387933*cent_jd**2)-(cent_jd**3/38710000))%360
    return np.radians(theta)

def ECEF_to_ECI(r_ecef,theta): # Will return an ECI position vector from an ECEF vector and a GMST angle
    cos,sin=np.cos(theta),np.sin(theta)
    R=np.array([[cos,-sin,0],[sin,cos,0],[0,0,1]]) # Rotation matrix around Z by a negative GMST
    return R @ r_ecef # the @ is numpys matrix multiplication, this will produce the 3x3 ECI vector

def ECI_to_ECEF(r_eci,theta):
    # Rotates an ECI vector to ECEF by applying Earths rotation
    cos, sin=np.cos(theta),np.sin(theta)
    R=([[cos,sin,0],[-sin,cos,0],[0,0,1]])
    return R @ r_eci
