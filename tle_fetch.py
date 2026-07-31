import requests
from sgp4.api import Satrec
from datetime import datetime, timezone

# SPOQC: 68423
# SPEQTRE: 66769

def fetch_tle(satellites: dict) -> dict:
    # e.g. {"SPOQC": 68423, "SPEQTRE": 66769}
    celestrak="https://celestrak.org/NORAD/elements/gp.php" # Our base url
    results={}

    for name, NORAD_ID in satellites.items():
        url=f"{celestrak}?CATNR={NORAD_ID}&FORMAT=TLE" # Building the URL for each satellite with the NORAD ID on celestrak
        response=requests.get(url,timeout=10) # Can add some error prevention later
        lines=response.text.strip().splitlines()

        if len(lines) == 3:
            TLE_1, TLE_2 = lines[1], lines[2]
        else:
            TLE_1, TLE_2 = lines[0], lines[1]
        sat=Satrec.twoline2rv(TLE_1,TLE_2)

        # Computing TLE Age (sat.jdsatepoch)
        epoch_jd=sat.jdsatepoch+sat.jdsatepochF
        now_jd=datetime.now(timezone.utc).timestamp() / 86400 + 2440587.5
        age_days=now_jd-epoch_jd

        results[name]={'sat': sat, 'norad': NORAD_ID, 'age': age_days}

        print(f"Loaded {name} (ID:{NORAD_ID}): "
              f"INC:{sat.inclo*180/3.14159265:.4f}' | "
              f"MM: {sat.no_kozai*(1440/(2*3.14159265)):.4f} rev/day | "
              f"TLE Age: {age_days:.1f} days")

    return results
