import calendar
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

ISO_DURATION_RE = re.compile(
    r"^P(?:(?P<years>\d+)Y)?(?:(?P<months>\d+)M)?(?:(?P<weeks>\d+)W)?(?:(?P<days>\d+)D)?$"
)

def parse_utc(value):
    if value is None:
        return None
    text=str(value)
    if text.endswith("Z"):
        text=text[:-1]+"+00:00"
    dt=datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise ValueError(f"Timezone offset required for normalized temporal value: {value}")
    return dt.astimezone(timezone.utc)

def iso_utc(dt):
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00","Z")

def parse_duration(text):
    m=ISO_DURATION_RE.match(str(text or ""))
    if not m:
        raise ValueError(f"Unsupported ISO calendar duration: {text}")
    vals={k:int(v or 0) for k,v in m.groupdict().items()}
    if not any(vals.values()):
        raise ValueError("Zero/empty temporal duration is not admitted in C4-011 fixtures")
    return vals

def add_months(dt, months):
    total=(dt.year*12+(dt.month-1))+months
    year=total//12
    month=total%12+1
    day=min(dt.day,calendar.monthrange(year,month)[1])
    return dt.replace(year=year,month=month,day=day)

def add_calendar_duration(dt, duration_text):
    p=parse_duration(duration_text)
    out=dt
    if p["years"]:
        out=add_months(out,p["years"]*12)
    if p["months"]:
        out=add_months(out,p["months"])
    if p["weeks"] or p["days"]:
        out=out+timedelta(weeks=p["weeks"],days=p["days"])
    return out

def fixed_duration_seconds(duration_text):
    p=parse_duration(duration_text)
    if p["years"] or p["months"]:
        return None
    return (p["weeks"]*7+p["days"])*86400

def dt_seconds(a,b):
    return (a-b).total_seconds()
