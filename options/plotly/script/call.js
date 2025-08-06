const fields = data.series[0].fields;
const get = name => fields.find(f => f.name === name)?.values?.toArray();

const x = get('strike_bucket');
const y = get('expiry');
const zRaw = get('last_crawled');
const oi = get('oi');

if (!x || !y || !zRaw || !oi) {
  throw new Error("Missing required fields");
}

// Convert to Date for sorting
const zDates = zRaw.map(v => new Date(v));
const zISO = zDates.map(d => d.toISOString());
const zLabel = zDates.map(d =>
  d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
);

// Sort by last_crawled ascending
const indices = zDates.map((_, i) => i).sort((a, b) => zDates[a] - zDates[b]);

const sortedStrike = indices.map(i => x[i]);
const sortedExpiry = indices.map(i => y[i]);
const sortedZ = indices.map(i => zISO[i]);
const sortedZLabel = indices.map(i => zLabel[i]);
const sortedOI = indices.map(i => oi[i]);

const trace = {
  x: sortedStrike,
  y: sortedExpiry,
  z: sortedZ,
  mode: 'markers',
  type: 'scatter3d',
  marker: {
    size: 5,
    color: sortedOI,
    colorscale: 'red', // ✅ warm-only color gradient
    colorbar: { title: 'Open Interest' },
    opacity: 0.9
  },
  text: sortedOI.map((v, i) =>
    `Strike: ${sortedStrike[i]}\nExpiry: ${sortedExpiry[i]}\nSnapshot: ${sortedZLabel[i]}\nOI: ${v}`
  ),
  hoverinfo: 'text',
  name: 'CALL OI'
};

return {
  data: [trace],
  layout: {
    scene: {
      xaxis: { title: 'Strike Bucket' },
      yaxis: { title: 'Expiration Date' },
      zaxis: {
        title: 'Snapshot Time (Last Crawled)',
        type: 'date'
      }
    },
    title: 'CALL OI Evolution',
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: { l: 0, r: 0, b: 0, t: 40 }
  }
};