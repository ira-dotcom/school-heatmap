# Where the good schools are

A heatmap of every public school in the nine Bay Area counties, shaded by the
share of its students who actually test proficient. Warm is higher. Pan, filter by grade
level, and the district ranking on the left recomputes for whatever is on
screen.

Built after [a reel from chloe.shih](https://www.instagram.com/reel/Dd4dgC_Ay5u/)
about hunting for schools during her third trimester, and the comment under it
asking how to build one for Seattle. This one does Seattle, or any other state,
with a one-word change.

## Run it

It is a static page. No build step, no keys, no server.

```
cd docs && python3 -m http.server 8000
```

Then open <http://localhost:8000>. Or turn on GitHub Pages for the `docs/`
folder and it is live as it is.

## Rebuild the data, or point it at another state

```
python3 tools/build_dataset.py --state CA                      # the whole state
python3 tools/build_dataset.py --state WA                      # somewhere else
python3 tools/build_dataset.py --state CA --counties 6037      # one county
```

Standard library only. The script pulls two public, key-free datasets from the
[Urban Institute Education Data API](https://educationdata.urban.org/documentation/)
and joins them on the federal school id:

| Source | What it gives |
| --- | --- |
| NCES Common Core of Data directory, 2022 | name, district, coordinates, grade level, enrollment, lunch program |
| EDFacts assessments, 2018 | percent proficient in reading and math, all students, all grades |

A school appears only if it is open, has real coordinates, and had at least 40
valid tests. That last rule drops about 1,500 California schools whose scores
are too thin to mean anything. Change it with `--min-tested`.

The committed `bay-area.json` is the statewide build narrowed to the nine Bay
Area counties, which keeps the page fast on a phone. To show somewhere else,
build its file and change the `fetch` path at the bottom of `docs/app.js`.

## The score, and what it is not

The number on every school is the plain average of its reading and math
proficiency rates. Nothing is weighted, modeled, or predicted, so any figure on
screen can be traced back to one of the two files above.

Proficiency is also the school statistic most closely tied to the income of the
families around it. A warm patch on this map says a district is resourced and
its families are comfortable, which is worth knowing if you are deciding where
to live, and is not a verdict on any individual teacher, child, or school. The
app says so on the page rather than only here.

The assessment data is from 2018, the most recent year EDFacts publishes
through this API with full coverage. Districts change. Treat the map as a place
to start a list, not to finish one.

## Layout

```
docs/            the site, and what GitHub Pages serves
  index.html
  app.js         map, filters, district board
  style.css
  data/         generated, committed so the page works with no setup
    bay-area.json
tools/
  build_dataset.py
```
