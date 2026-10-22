#!/usr/bin/env python3
import os
import json
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from location import ensure_location, handle_location_command

HOME = Path.home()
TZ = ZoneInfo("America/Chicago")
BLUE = "\033[38;2;0;191;255m"
RESET = "\033[0m"


def query(database, sql, params=(), default=None):
    if not database.exists():
        return default
    with sqlite3.connect(database) as connection:
        row = connection.execute(sql, params).fetchone()
    return row[0] if row else default


def memory_percent():
    values = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        values[key] = int(value.split()[0])
    return round((values["MemTotal"] - values["MemAvailable"]) / values["MemTotal"] * 100)


def temperature():
    output = subprocess.run(["sensors"], capture_output=True, text=True, check=False).stdout
    for line in output.splitlines():
        if "Package id 0:" in line or line.strip().startswith("Tctl:"):
            for part in line.split():
                if part.startswith("+"):
                    return part.replace("°", "")
    return "N/A"


def source_age(timestamp):
    if not timestamp:
        return "unavailable"
    latest = datetime.fromisoformat(timestamp).replace(tzinfo=TZ)
    delta = datetime.now(TZ) - latest
    return f"{delta.days}d {delta.seconds // 3600}h"


def main():
    if handle_location_command(sys.argv[1:]):
        return
    now = datetime.now(TZ)
    today = now.strftime("%Y-%m-%d")
    aircraft_db = HOME / ".local/share/kanslor-aircraft/history.sqlite3"
    crime_db = HOME / ".local/share/kanslor-crime/history.sqlite3"
    weather_db = HOME / ".local/share/kanslor-weather/history.sqlite3"
    location = ensure_location(interactive=True)
    start = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())

    aircraft_today = query(aircraft_db, "SELECT COUNT(*) FROM sightings WHERE seen_at >= ?", (start,), 0)
    military_today = query(aircraft_db, "SELECT COUNT(*) FROM sightings s WHERE seen_at >= ? AND s.hex IN (SELECT hex FROM aircraft_metadata WHERE classification = 'MIL')", (start,), 0)
    law_today = query(aircraft_db, "SELECT COUNT(*) FROM sightings s WHERE seen_at >= ? AND s.hex IN (SELECT hex FROM aircraft_metadata WHERE classification = 'LE')", (start,), 0)
    crime_today = query(crime_db, "SELECT COUNT(*) FROM calls WHERE response_at LIKE ?", (f"{today}%",), 0)
    crime_latest = query(crime_db, "SELECT MAX(response_at) FROM calls", default=None)
    active_alerts = query(weather_db, "SELECT COUNT(*) FROM alerts WHERE active = 1", default=0)
    condition = None
    if weather_db.exists():
        with sqlite3.connect(weather_db) as connection:
            condition = connection.execute("SELECT description, temperature_f, humidity, wind_mph, wind_direction FROM conditions ORDER BY observed_at DESC LIMIT 1").fetchone()

    disk = shutil.disk_usage("/")
    updates = subprocess.run(["bash", "-lc", "grep -Eo '[0-9]+ updates can be applied immediately' /var/lib/update-notifier/updates-available 2>/dev/null | head -1 | awk '{print $1}'"], capture_output=True, text=True, check=False).stdout.strip() or "0"
    reboot = "REQUIRED" if Path("/var/run/reboot-required").exists() else "not required"
    failed = subprocess.run(["systemctl", "--failed", "--no-legend"], capture_output=True, text=True, check=False).stdout.splitlines()

    print(f"{BLUE}K A N S L O R  //  DAILY BRIEFING{RESET}")
    print(f"{BLUE}{now.strftime('%A, %B %d %Y %H:%M %Z')}{RESET}\n")
    print(f"AREA     {location['name']} | ZIP {location['zip_code']} | aircraft radius {location['radius_miles']:.1f} mi")
    if condition:
        description, temp, humidity, wind, direction = condition
        wind_text = f"{wind:.0f} mph" if wind is not None else "--"
        print(f"WEATHER  {description or '--'} | {temp:.0f}F | humidity {humidity:.0f}% | wind {wind_text}")
    else:
        print("WEATHER  no current observation")
    print(f"ALERTS   {active_alerts} active NWS alert(s)")
    print(f"AIRCRAFT {aircraft_today} sighting(s) today | {military_today} likely military | {law_today} likely law enforcement")
    print(f"CRIME    {crime_today} call(s) dated today | source latest {crime_latest or '--'} | age {source_age(crime_latest)}")
    print(f"SYSTEM   load {os.getloadavg()[0]:.2f} | memory {memory_percent()}% | disk {disk.used / disk.total * 100:.0f}% | temp {temperature()}")
    print(f"MAINT    {updates} update(s) | reboot {reboot} | failed units {len(failed)}")


if __name__ == "__main__":
    main()
