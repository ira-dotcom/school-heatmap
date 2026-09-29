# Where the good schools are

A heatmap of every public school around the Bay, shaded by the share of its
students who actually test proficient. Warm is higher. Pan, filter by grade
level, and the district ranking on the left recomputes for whatever is on
screen.

Built after [a reel from chloe.shih](https://www.instagram.com/reel/Dd4dgC_Ay5u/)
about hunting for schools during her third trimester, and the comment under it
asking how to build one for Seattle. This one does Seattle, or any other state,
with a one-word change.

## Run it

Two steps, no keys, no build tooling, no server beyond Python's own.

```
python3 tools/build_dataset.py --state CA --counties 6001,6013,6041,6055,6075,6081,6085,6095,6097 --out docs/data/bay-area.json
cd docs && python3 -m http.server 8000
```

Then open <http://localhost:8000>. The first command takes about a minute and
writes roughly 1,600 schools; the page reads that one file and nothing else.

The dataset is not committed. It is 400 KB of regenerable output, and keeping
it out means the numbers in the repo can never quietly go stale against the
source. Run the first command again whenever you want them refreshed. To put
the map on GitHub Pages, build the file, commit it, and point Pages at `docs/`.

## Point it somewhere else

```
python3 tools/build_dataset.py --state CA                 # the whole state, 8,960 schools
python3 tools/build_dataset.py --state WA                 # Seattle, per the comments
python3 tools/build_dataset.py --state CA --counties 6037 # one county
```

Standard library only. The script pulls two public, key-free datasets from the
[Urban Institute Education Data API](https://educationdata.urban.org/documentation/)
and joins them on the federal school id:

| Source | What it gives |
| --- | --- |
| NCES Common Core of Data directory, 2022 | name, district, coordinates, grade level, enrollment, lunch program |
| EDFacts assessments, 2018 | percent proficient in reading and math, all students, all grades |

A school appears only if it is open, physical rather than virtual, has real
coordinates, and had at least 40 valid tests. That last rule drops about 1,500
California schools whose scores are too thin to mean anything. Change it with
`--min-tested`.

Writing anywhere other than `docs/data/bay-area.json` means changing the
`fetch` path at the bottom of `docs/app.js` to match.

## The score, and what it is not

The number on every school is the plain average of its reading and math
proficiency rates. Nothing is weighted, modeled, or predicted, so any figure on
screen traces back to one of the two files above.

Proficiency is also the school statistic most closely tied to the income of the
families around it. A warm patch says a district is resourced and its families
are comfortable, which is worth knowing if you are deciding where to live, and
is not a verdict on any individual teacher, child, or school. The app says that
on the page, not only here.

The assessment data is from 2018, the most recent year EDFacts publishes
through this API with full coverage. Districts change. Treat the map as a place
to start a list, not to finish one.

## Layout

```
docs/              the site, and what GitHub Pages would serve
  index.html
  app.js           map, filters, district board, school detail
  style.css
  data/            where the generated JSON lands
tools/
  build_dataset.py the only thing that touches the network
```
