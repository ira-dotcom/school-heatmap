#!/usr/bin/env python3
"""Build the school dataset the map reads.

Pulls two public, key-free datasets from the Urban Institute Education Data API
and joins them on the federal school id (ncessch):

  * CCD directory   -> name, district, coordinates, level, enrollment
  * EDFacts results -> percent of students proficient in reading and math

Writes docs/data/<state>.json, which is the only thing the web app loads.

    python3 tools/build_dataset.py --state CA
    python3 tools/build_dataset.py --state WA
    python3 tools/build_dataset.py --state CA --counties 6001,6075 --out docs/data/bay-area.json

Every number in the output came from one of those two files. Nothing is
modeled, predicted, or filled in.
"""

import argparse
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://educationdata.urban.org/api/v1"

# FIPS codes, so --state takes a postal abbreviation like a person would type.
FIPS = {
    "AL": 1, "AK": 2, "AZ": 4, "AR": 5, "CA": 6, "CO": 8, "CT": 9, "DE": 10,
    "DC": 11, "FL": 12, "GA": 13, "HI": 15, "ID": 16, "IL": 17, "IN": 18,
    "IA": 19, "KS": 20, "KY": 21, "LA": 22, "ME": 23, "MD": 24, "MA": 25,
    "MI": 26, "MN": 27, "MS": 28, "MO": 29, "MT": 30, "NE": 31, "NV": 32,
    "NH": 33, "NJ": 34, "NM": 35, "NY": 36, "NC": 37, "ND": 38, "OH": 39,
    "OK": 40, "OR": 41, "PA": 42, "RI": 44, "SC": 45, "SD": 46, "TN": 47,
    "TX": 48, "UT": 49, "VT": 50, "VA": 51, "WA": 53, "WV": 54, "WI": 55,
    "WY": 56,
}

LEVELS = {"1": "elementary", "2": "middle", "3": "high", "4": "other"}


def fetch(url, tries=4):
    """GET one page of JSON, retrying on the API's occasional 500s."""
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "school-heatmap (github.com/ira-dotcom)",
                    "Accept-Encoding": "gzip",
                },
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                body = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
            return json.loads(body)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as err:
            if attempt == tries - 1:
                raise
            wait = 2 ** attempt
            print(f"  retrying in {wait}s after {err}", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def pages(url):
    """Walk the API's next links, yielding every result row."""
    seen = 0
    while url:
        payload = fetch(url)
        rows = payload.get("results", [])
        seen += len(rows)
        print(f"  {seen} rows", file=sys.stderr)
        yield from rows
        url = payload.get("next")


def directory(fips, year):
    url = f"{API}/schools/ccd/directory/{year}/?fips={fips}"
    out = {}
    for row in pages(url):
        lat, lon = row.get("latitude"), row.get("longitude")
        # An open school with real coordinates, or it cannot go on a map.
        if lat is None or lon is None or lat == 0 or lon == 0:
            continue
        if str(row.get("school_status")) not in ("1", "3", "8"):
            continue
        if row.get("virtual") in (1, 2):
            continue
        out[row["ncessch"]] = {
            "name": (row.get("school_name") or "").strip(),
            "district": (row.get("lea_name") or "").strip(),
            "city": (row.get("city_location") or "").strip().title(),
            "county": row.get("county_code"),
            "lat": round(float(lat), 5),
            "lon": round(float(lon), 5),
            "level": LEVELS.get(str(row.get("school_level")), "other"),
            "enrollment": row.get("enrollment"),
            "charter": row.get("charter") == 1,
            "frpl": row.get("free_or_reduced_price_lunch"),
        }
    return out


def assessments(fips, year):
    """All-students, all-grades proficiency for every school in the state."""
    url = f"{API}/schools/edfacts/assessments/{year}/grade-99/?fips={fips}"
    out = {}
    for row in pages(url):
        read = row.get("read_test_pct_prof_midpt")
        math = row.get("math_test_pct_prof_midpt")
        if read is None or math is None or read < 0 or math < 0:
            continue
        tested = (row.get("read_test_num_valid") or 0) + (row.get("math_test_num_valid") or 0)
        out[row["ncessch"]] = {
            "read": round(float(read), 1),
            "math": round(float(math), 1),
            "tested": tested,
        }
    return out


def build(state, dir_year, assess_year, min_tested, counties=()):
    fips = FIPS[state]
    print(f"directory {dir_year}", file=sys.stderr)
    schools = directory(fips, dir_year)
    print(f"assessments {assess_year}", file=sys.stderr)
    scores = assessments(fips, assess_year)

    rows = []
    for ncessch, school in schools.items():
        score = scores.get(ncessch)
        if not score:
            continue
        # A handful of students tested is noise, not a signal about a school.
        if score["tested"] < min_tested:
            continue
        if counties and str(school.get("county")) not in counties:
            continue
        school = dict(school)
        school["read"] = score["read"]
        school["math"] = score["math"]
        school["score"] = round((score["read"] + score["math"]) / 2, 1)
        school["tested"] = score["tested"]
        school["id"] = ncessch
        rows.append(school)

    rows.sort(key=lambda r: -r["score"])
    return {
        "state": state,
        "directory_year": dir_year,
        "assessment_year": assess_year,
        "min_tested": min_tested,
        "counties": list(counties),
        "source": "Urban Institute Education Data API (NCES CCD + EDFacts)",
        "source_url": "https://educationdata.urban.org/documentation/",
        "built": time.strftime("%Y-%m-%d"),
        "count": len(rows),
        "schools": rows,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state", default="CA", help="postal abbreviation, e.g. CA")
    ap.add_argument("--directory-year", type=int, default=2022)
    ap.add_argument("--assessment-year", type=int, default=2018)
    ap.add_argument("--min-tested", type=int, default=40,
                    help="drop schools with fewer valid tests than this")
    ap.add_argument("--counties", default="",
                    help="comma separated county FIPS to keep, e.g. 6001,6075. "
                         "Empty keeps the whole state.")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    state = args.state.upper()
    if state not in FIPS:
        ap.error(f"unknown state {state}")

    counties = tuple(c.strip() for c in args.counties.split(",") if c.strip())
    data = build(state, args.directory_year, args.assessment_year,
                 args.min_tested, counties)
    out = args.out or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs", "data", f"{state}.json",
    )
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump(data, fh, separators=(",", ":"))
    print(f"wrote {data['count']} schools to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
