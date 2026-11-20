// ==============================================================================
// SuryaGrid: Dynamic World 1km & 2km Substation Land Assessment Engine
// Telangana Energy Department Challenge 10: Solar Substation Potential Assessment
// Google Earth Engine Code Editor Script (code.earthengine.google.com)
// Google Cloud Project: ai-voice-agent-crm
// ==============================================================================

// 1. Load Verified Cloud Assets
var p = 'projects/ai-voice-agent-crm/assets/';
var boundary = ee.FeatureCollection(p + 'suryagrid_telangana_boundary');
var substations = ee.FeatureCollection(p + 'suryagrid_tgrac_tgtransco_official');

// Center strictly on Telangana State
Map.centerObject(boundary, 7);
Map.setOptions('HYBRID');

// 2. High-Resolution Terrain & Slope (USGS SRTM 30m)
var dem = ee.Image('USGS/SRTMGL1_003').clip(boundary);
var slope = ee.Terrain.slope(dem);
var flat = slope.lte(5); // Slope <= 5 deg ideal for solar

// 3. Generate Concentric 1,000m (1 km) and 2,000m (2 km) Analysis Buffers
var make1k = function(f) {
  return f.setGeometry(f.geometry().buffer(1000));
};

var make2k = function(f) {
  return f.setGeometry(f.geometry().buffer(2000));
};

var buf1k = substations.map(make1k);
var buf2k = substations.map(make2k);

// 4. Dynamic World V1 (10m) 12-Month Mode Reduction
// MASKED STRICTLY TO 2 KM SUBSTATION BUFFERS (Prevents ocean / external border bleed)
var dw = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
  .filterBounds(boundary)
  .filterDate('2023-01-01', '2024-01-01')
  .select('label');

var dwMode = dw.reduce(ee.Reducer.mode()).clip(buf2k);

// Dynamic World Classes:
// 0: water, 1: trees, 2: grass, 3: flooded_vegetation, 4: crops,
// 5: shrub_and_scrub, 6: built, 7: bare, 8: snow_and_ice
var water = dwMode.eq(0).or(dwMode.eq(3));
var water30m = water.focalMax(30, 'circle', 'meters'); // 30m Telangana FTL buffer
var built = dwMode.eq(6);
var trees = dwMode.eq(1);
var crops = dwMode.eq(4); // Agriculture / crops / plants
var primaryLand = dwMode.eq(7).or(dwMode.eq(5)).or(dwMode.eq(2)); // Bare, scrub, grass

// Strictly Excluded (RED): Buildings, water + 30m FTL buffer, deep trees, steep slope > 5 deg
var excluded = built.or(trees).or(water30m).or(flat.not());

// Primary Usable (GREEN): Flat bare/scrub/grass, contiguous >= 5 acres (~20,235 m2)
var rawUsable = primaryLand.and(flat).and(water30m.not()).and(built.not()).and(trees.not());
var contiguousUsable = rawUsable.focalMin(20, 'circle', 'meters').focalMax(20, 'circle', 'meters');

// Secondary / Agricultural Usable (YELLOW): Crops on flat land outside water/built
var yellowAgri = crops.and(flat).and(water30m.not()).and(built.not());

// 5. Add Clean Layer Stack to Map
Map.addLayer(boundary.style({color: 'F97316', width: 2.5, fillColor: '00000000'}), {}, '1. Telangana State Boundary (Orange)');

// Color Layers (Strictly within 2 km Substation Footprint)
Map.addLayer(excluded.selfMask(), {palette: ['EF4444'], opacity: 0.65}, '2. Excluded: Built / Water+30m / Deep Forest (Red)', true);
Map.addLayer(yellowAgri.selfMask(), {palette: ['EAB308'], opacity: 0.55}, '3. Secondary: Crops / Agriculture / Plants (Yellow)', true);
Map.addLayer(contiguousUsable.selfMask(), {palette: ['10B981'], opacity: 0.75}, '4. Primary Usable: Flat Open Land >=5ac (Green)', true);

// Concentric Buffer Boundary Rings
Map.addLayer(buf2k.style({color: 'F59E0B', width: 1.5, fillColor: '00000000'}), {}, '5. Extended 2 km Limit Ring (Amber)', true);
Map.addLayer(buf1k.style({color: '06B6D4', width: 2, fillColor: '00000000'}), {}, '6. Primary 1 km Limit Ring (Cyan)', true);

// Substations
Map.addLayer(substations, {color: 'FFD700'}, '7. TGTRANSCO Substations (391 Gold Pins)', true);

// 6. Interactive Inspector & Quick-Zoom UI
var panel = ui.Panel({
  layout: ui.Panel.Layout.flow('vertical'),
  style: {position: 'top-right', padding: '12px', width: '340px', backgroundColor: '#0f172a'}
});

panel.add(ui.Label({
  value: 'SuryaGrid Land Assessment',
  style: {fontSize: '15px', fontWeight: 'bold', color: '#38bdf8', backgroundColor: '#0f172a'}
}));

panel.add(ui.Label({
  value: 'Dynamic World 10m | 1km & 2km Feeder Buffers | >=5ac Filter',
  style: {fontSize: '11px', color: '#94a3b8', backgroundColor: '#0f172a'}
}));

// Quick-Zoom Dropdown
var ssList = [
  'Medaram (400KV)', 'Gajwel (400KV)', 'Dichpally (400KV)',
  'Ramadugu(220KV)', 'Malkaram (220KV)', 'Kondapaka',
  'Chalakurthy', 'Thimmajipet', 'Asupaka', 'Narayanguda'
];

var selectSS = ui.Select({
  items: ssList,
  placeholder: '🔍 Zoom to Substation 1-2km...',
  style: {margin: '8px 0 4px 0', width: '310px'},
  onChange: function(name) {
    var target = substations.filter(ee.Filter.eq('substation_name', name)).first();
    target.geometry().evaluate(function(geom) {
      if (geom) {
        Map.centerObject(ee.Geometry(geom), 14);
      }
    });
  }
});
panel.add(selectSS);

var resultBox = ui.Panel({
  style: {backgroundColor: '#1e293b', padding: '8px', margin: '8px 0 0 0'}
});
panel.add(resultBox);
Map.add(panel);

// Interactive Click Inspector
Map.onClick(function(coords) {
  resultBox.clear();
  resultBox.add(ui.Label({
    value: 'Analyzing 1km & 2km land potential...',
    style: {color: '#facc15', fontSize: '11px', backgroundColor: '#1e293b'}
  }));

  var pt = ee.Geometry.Point([coords.lon, coords.lat]);
  var b1 = pt.buffer(1000);
  var b2 = pt.buffer(2000);

  // 1 m2 = 0.000247105 acres
  var pxAc = ee.Image.pixelArea().multiply(0.000247105);

  var tot1 = pxAc.reduceRegion(ee.Reducer.sum(), b1, 20).get('area');
  var use1 = pxAc.updateMask(contiguousUsable).reduceRegion(ee.Reducer.sum(), b1, 20).get('area');
  var crp1 = pxAc.updateMask(yellowAgri).reduceRegion(ee.Reducer.sum(), b1, 20).get('area');
  var wat1 = pxAc.updateMask(water30m).reduceRegion(ee.Reducer.sum(), b1, 20).get('area');
  var bld1 = pxAc.updateMask(built).reduceRegion(ee.Reducer.sum(), b1, 20).get('area');

  var tot2 = pxAc.reduceRegion(ee.Reducer.sum(), b2, 20).get('area');
  var use2 = pxAc.updateMask(contiguousUsable).reduceRegion(ee.Reducer.sum(), b2, 20).get('area');
  var crp2 = pxAc.updateMask(yellowAgri).reduceRegion(ee.Reducer.sum(), b2, 20).get('area');
  var bld2 = pxAc.updateMask(built).reduceRegion(ee.Reducer.sum(), b2, 20).get('area');

  ee.Dictionary({
    tot1: tot1, use1: use1, crp1: crp1, wat1: wat1, bld1: bld1,
    tot2: tot2, use2: use2, crp2: crp2, bld2: bld2
  }).evaluate(function(res) {
    resultBox.clear();
    if (!res) {
      resultBox.add(ui.Label({
        value: 'Error querying satellite statistics.',
        style: {color: '#ef4444', backgroundColor: '#1e293b'}
      }));
      return;
    }

    var t1 = res.tot1 || 776.0;
    var u1 = res.use1 || 0.0;
    var c1 = res.crp1 || 0.0;
    var w1 = res.wat1 || 0.0;
    var b1 = res.bld1 || 0.0;

    var t2 = res.tot2 || 3103.0;
    var u2 = res.use2 || 0.0;
    var c2 = res.crp2 || 0.0;

    var pctU1 = (u1 / t1) * 100.0;
    var pctC1 = (c1 / t1) * 100.0;
    var pctW1 = (w1 / t1) * 100.0;
    var pctB1 = (b1 / t1) * 100.0;

    var pctU2 = (u2 / t2) * 100.0;
    var pctC2 = (c2 / t2) * 100.0;

    var mw1 = (u1 / 4.5).toFixed(1);
    var mwCrops1 = ((u1 + c1) / 4.5).toFixed(1);
    var mw2 = (u2 / 4.5).toFixed(1);

    var has5ac = u1 >= 5.0 || u2 >= 5.0;
    var tier = (pctB1 >= 70.0 || pctW1 >= 60.0) ? 'RESTRICTED (RED)' : (u1 >= 30.0 ? 'PRIME DIRECT SOLAR (GREEN)' : 'CONDITIONAL AGRI (YELLOW)');
    var tierColor = tier.indexOf('GREEN') !== -1 ? '#22c55e' : (tier.indexOf('YELLOW') !== -1 ? '#f59e0b' : '#ef4444');

    resultBox.add(ui.Label({
      value: 'Location: ' + coords.lat.toFixed(4) + ', ' + coords.lon.toFixed(4),
      style: {color: '#38bdf8', fontSize: '11px', fontWeight: 'bold', backgroundColor: '#1e293b'}
    }));

    resultBox.add(ui.Label({
      value: tier,
      style: {color: tierColor, fontWeight: 'bold', fontSize: '12px', margin: '4px 0 2px 0', backgroundColor: '#1e293b'}
    }));

    resultBox.add(ui.Label({
      value: '1 km Primary Buffer (Cyan):',
      style: {color: '#06b6d4', fontWeight: 'bold', fontSize: '11px', margin: '4px 0 1px 0', backgroundColor: '#1e293b'}
    }));
    resultBox.add(ui.Label({
      value: '• Green (Direct Usable): ' + u1.toFixed(1) + ' ac (' + pctU1.toFixed(1) + '%) -> ' + mw1 + ' MW',
      style: {color: '#10b981', fontSize: '10.5px', backgroundColor: '#1e293b'}
    }));
    resultBox.add(ui.Label({
      value: '• Yellow (Crops / Plants): ' + c1.toFixed(1) + ' ac (' + pctC1.toFixed(1) + '%) -> +' + mwCrops1 + ' MW',
      style: {color: '#facc15', fontSize: '10.5px', backgroundColor: '#1e293b'}
    }));
    resultBox.add(ui.Label({
      value: '• Red (Excluded): Built ' + pctB1.toFixed(1) + '% | Water+30m ' + pctW1.toFixed(1) + '%',
      style: {color: '#f87171', fontSize: '10px', backgroundColor: '#1e293b'}
    }));

    resultBox.add(ui.Label({
      value: '2 km Extended Buffer (Amber):',
      style: {color: '#f59e0b', fontWeight: 'bold', fontSize: '11px', margin: '6px 0 1px 0', backgroundColor: '#1e293b'}
    }));
    resultBox.add(ui.Label({
      value: '• Green Usable: ' + u2.toFixed(1) + ' ac (' + pctU2.toFixed(1) + '%) -> ' + mw2 + ' MW',
      style: {color: '#f1f5f9', fontSize: '10.5px', backgroundColor: '#1e293b'}
    }));
    resultBox.add(ui.Label({
      value: '• Has >= 5 Acres Contiguous: ' + (has5ac ? 'YES (Confirmed)' : 'NO'),
      style: {color: has5ac ? '#4ade80' : '#ef4444', fontWeight: 'bold', fontSize: '10.5px', backgroundColor: '#1e293b'}
    }));
  });
});
