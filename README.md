# Daily Briefing

Terminal summary of the Kanslor local monitoring data.

Run `python3 briefing.py`. The first run asks for a five-digit United States ZIP code. Change it later with `python3 briefing.py --set-zip [ZIP_CODE]`.

This project reads the local SQLite histories produced by the companion monitoring apps and uses only the Python standard library.

Local location settings and generated caches are excluded from source control.
