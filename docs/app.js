/* Where the good schools are.
   One fetch, one heat layer, and filters that recompute both.
   Everything on screen comes out of the JSON in docs/data. */

const GRADIENT = { 0.0: '#4a7fd4', 0.35: '#58c3a8', 0.6: '#f3d34a', 0.8: '#ef8b3c', 1.0: '#d94848' };

const map = L.map('map', { zoomControl: true, preferCanvas: true })
  .setView([37.78, -122.24], 10);

L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; OpenStreetMap, &copy; CARTO',
  maxZoom: 19,
}).addTo(map);

const el = (id) => document.getElementById(id);

const state = {
  all: [],
  levels: new Set(['elementary', 'middle', 'high']),
  floor: 0,
  charter: true,
  pins: false,
  query: '',
};

let heat = null;
const markers = L.layerGroup().addTo(map);

function colorFor(score) {
  if (score >= 80) return '#d94848';
  if (score >= 60) return '#ef8b3c';
  if (score >= 40) return '#f3d34a';
  if (score >= 20) return '#58c3a8';
  return '#4a7fd4';
}

function visible() {
  const q = state.query.trim().toLowerCase();
  return state.all.filter((s) => {
    if (!state.levels.has(s.level)) return false;
    if (s.score < state.floor) return false;
    if (!state.charter && s.charter) return false;
    if (q && !(s.city.toLowerCase().includes(q)
            || s.district.toLowerCase().includes(q)
            || s.name.toLowerCase().includes(q))) return false;
    return true;
  });
}

function draw() {
  const rows = visible();

  if (heat) map.removeLayer(heat);
  heat = L.heatLayer(
    // Weight by proficiency squared, so a strong school reads as strong instead
    // of every school washing the map to the same middling orange.
    rows.map((s) => [s.lat, s.lon, Math.pow(s.score / 100, 2)]),
    { radius: 26, blur: 20, maxZoom: 13, minOpacity: 0.28, gradient: GRADIENT },
  ).addTo(map);

  markers.clearLayers();
  const showPins = state.pins || rows.length <= 500;
  if (showPins) {
    rows.forEach((s) => {
      L.circleMarker([s.lat, s.lon], {
        radius: 4.5,
        color: '#fff',
        weight: 1,
        fillColor: colorFor(s.score),
        fillOpacity: 0.95,
      })
        .on('click', () => showDetail(s))
        .bindTooltip(`${s.name} \u2014 ${s.score}%`, { direction: 'top' })
        .addTo(markers);
    });
  }

  el('count').textContent = rows.length
    ? `${rows.length.toLocaleString()} schools${showPins ? '' : ', narrow the filters or tick the box to see individual pins'}`
    : 'Nothing matches those filters.';

  board(rows);
}

function board(rows) {
  const bounds = map.getBounds();
  const byDistrict = new Map();
  rows.forEach((s) => {
    if (!bounds.contains([s.lat, s.lon])) return;
    const d = byDistrict.get(s.district) || { total: 0, n: 0 };
    d.total += s.score;
    d.n += 1;
    byDistrict.set(s.district, d);
  });

  const ranked = [...byDistrict.entries()]
    .filter(([, d]) => d.n >= 3)
    .map(([name, d]) => ({ name, avg: d.total / d.n, n: d.n }))
    .sort((a, b) => b.avg - a.avg)
    .slice(0, 12);

  el('districts').innerHTML = ranked.length
    ? ranked.map((d) =>
        `<li>${d.name} <span>${d.avg.toFixed(0)}% \u00b7 ${d.n} schools</span></li>`).join('')
    : '<li class="hint">Pan somewhere with at least three schools.</li>';
}

function showDetail(s) {
  const frpl = s.frpl && s.enrollment
    ? `${Math.round((s.frpl / s.enrollment) * 100)}% of students`
    : 'not reported';
  el('detail').className = 'detail';
  el('detail').innerHTML = `
    <h3>${s.name}</h3>
    <p class="where">${s.district} \u00b7 ${s.city}${s.charter ? ' \u00b7 charter' : ''}</p>
    <dl>
      <dt>Proficient overall</dt><dd>${s.score}%</dd>
      <dt>Reading</dt><dd>${s.read}%</dd>
      <dt>Math</dt><dd>${s.math}%</dd>
      <dt>Enrollment</dt><dd>${s.enrollment ? s.enrollment.toLocaleString() : 'not reported'}</dd>
      <dt>Free or reduced lunch</dt><dd>${frpl}</dd>
    </dl>`;
}

function flyToQuery() {
  const q = state.query.trim().toLowerCase();
  if (q.length < 3) return;
  const hits = state.all.filter((s) =>
    s.city.toLowerCase().includes(q) || s.district.toLowerCase().includes(q));
  if (!hits.length) return;
  map.fitBounds(L.latLngBounds(hits.map((s) => [s.lat, s.lon])).pad(0.12));
}

let typing;
el('search').addEventListener('input', (e) => {
  state.query = e.target.value;
  clearTimeout(typing);
  typing = setTimeout(() => { draw(); flyToQuery(); }, 220);
});

el('levels').addEventListener('click', (e) => {
  const chip = e.target.closest('.chip');
  if (!chip) return;
  const level = chip.dataset.level;
  if (state.levels.has(level)) state.levels.delete(level);
  else state.levels.add(level);
  chip.classList.toggle('on');
  draw();
});

el('floor').addEventListener('input', (e) => {
  state.floor = Number(e.target.value);
  el('floorValue').textContent = state.floor;
  draw();
});

el('charter').addEventListener('change', (e) => { state.charter = e.target.checked; draw(); });
el('pins').addEventListener('change', (e) => { state.pins = e.target.checked; draw(); });
map.on('moveend', () => board(visible()));

fetch('data/bay-area.json')
  .then((r) => {
    if (!r.ok) throw new Error(`${r.status} loading the dataset`);
    return r.json();
  })
  .then((data) => {
    state.all = data.schools;
    el('provenance').innerHTML =
      `${data.count.toLocaleString()} public schools across the nine Bay Area counties.
       Proficiency from EDFacts ${data.assessment_year}, locations and enrollment from the
       NCES Common Core of Data ${data.directory_year}, both through the
       <a href="${data.source_url}">Urban Institute Education Data API</a>.
       Schools with fewer than ${data.min_tested} valid tests are left out.
       Built ${data.built}.`;
    draw();
  })
  .catch((err) => {
    el('count').textContent = `Could not load the data: ${err.message}`;
  });
