const get = (id) => document.getElementById(id);

const growthRates = { Central: 0.8, Resilience: 1.4, Transformation: 2.2 };
const years = [2026, 2027, 2028, 2029, 2030];
const scenario = get('scenario');
const productivity = get('productivity');
const start = get('start');
const energy = get('energy');
const comparison = get('comparison');

function project(name, productivityGain = 0, startYear = 2027, energyDeviation = 0) {
  let index = 100;
  return years.map((year) => {
    if (year > years[0]) {
      const gain = year >= startYear ? productivityGain : 0;
      const growth = growthRates[name] + gain - 0.35 * energyDeviation;
      index *= 1 + growth / 100;
    }
    return index;
  });
}

function draw(primary, baseline) {
  const values = [...primary, ...baseline];
  const low = Math.floor((Math.min(...values) - 1) / 5) * 5;
  const high = Math.ceil((Math.max(...values) + 1) / 5) * 5;
  const x = (index) => 56 + index * 107;
  const y = (value) => 202 - (value - low) / (high - low) * 180;
  const points = (series) => series.map((value, index) => `${x(index)},${y(value)}`).join(' ');
  const grid = [];
  for (let tick = low; tick <= high; tick += 5) {
    grid.push(`<line class="gridline" x1="56" x2="484" y1="${y(tick)}" y2="${y(tick)}"/><text x="44" y="${y(tick)}" text-anchor="end" dominant-baseline="middle">${tick}</text>`);
  }
  const labels = years.map((year, index) => `<text x="${x(index)}" y="228" text-anchor="middle">${year}</text>`);
  get('chart').innerHTML = [
    ...grid,
    ...labels,
    baseline.length ? `<polyline class="line comparison" points="${points(baseline)}"/>` : '',
    `<polyline class="line primary" points="${points(primary)}"/>`,
  ].join('');
}

function updateScenario() {
  const primary = project(scenario.value, Number(productivity.value), Number(start.value), Number(energy.value));
  const baseline = comparison.value === 'None' ? [] : project(comparison.value);
  const primaryEnd = primary.at(-1).toFixed(1);
  const comparisonEnd = baseline.length ? ` · Comparison ${baseline.at(-1).toFixed(1)}` : '';

  get('productivity-value').value = `${productivity.value}%`;
  get('energy-value').value = `${Number(energy.value) > 0 ? '+' : ''}${energy.value}%`;
  get('readout').textContent = `2030 illustrative index · Adjusted ${primaryEnd}${comparisonEnd}`;
  get('primary-key').textContent = `${scenario.value} (adjusted)`;
  get('comparison-key').hidden = !baseline.length;
  get('comparison-key').textContent = `${comparison.value} (unadjusted)`;
  get('trajectory').innerHTML = years.map((year, index) =>
    `<tr><th scope="row">${year}</th><td>${primary[index].toFixed(1)}</td><td>${baseline[index]?.toFixed(1) ?? '—'}</td></tr>`
  ).join('');
  draw(primary, baseline);
}

for (const control of [scenario, productivity, start, energy, comparison]) {
  control.addEventListener('input', updateScenario);
}
updateScenario();

const contact = get('contact-form');
contact.addEventListener('submit', (event) => {
  event.preventDefault();
  contact.reset();
  get('contact-status').textContent = 'Preview complete. No enquiry was sent.';
});
contact.querySelector('button').disabled = false;
