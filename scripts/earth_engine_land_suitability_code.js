// ==============================================================================
// SuryaGrid: Substation 0-3 km & 3-5 km Land, Terrain & Slope Suitability Engine
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

// 2. High-Resolution Terrain & Slope (USGS SRTM 30m) - Strictly Clipped to Telangana
var dem = ee.Image('USGS/SRTMGL1_003').clip(boundary);
var slope = ee.Terrain.slope(dem);
var steep = slope.gt(5);

// 3. Generate Concentric 0-3 km and 3-5 km Buffer Boundaries
var make3k = function(f) {
  return f.setGeometry(f.geometry().buffer(3000));
};

var make5k = function(f) {
  return f.setGeometry(f.geometry().buffer(5000));
};

var buf3k = substations.map(make3k);
var buf5k = substations.map(make5k);

// 4. Land Cover (ESA WorldCover 10m) - MASKED STRICTLY TO 5 KM SUBSTATION BUFFERS!
// (Prevents oceans, coasts, or anything outside Telangana from rendering)
var wc = ee.ImageCollection('ESA/WorldCover/v200').first().clip(buf5k);
var water = wc.eq(80).or(wc.eq(90));
var built = wc.eq(50);
var forest = wc.eq(10);
var unusable = water.or(built).or(forest).or(steep);
var usable = unusable.not();

// 5. Add Clean Visual Layers to Map
Map.addLayer(boundary.style({color: 'F97316', width: 2.5, fillColor: '00000000'}), {}, '1. Telangana State Boundary (Orange)');
Map.addLayer(water.selfMask(), {palette: ['0080ff']}, '2. Lakes & Water Bodies in 5km (Blue)', true);
Map.addLayer(built.selfMask(), {palette: ['ef4444']}, '3. Buildings & Settlements in 5km (Red)', true);
Map.addLayer(usable.selfMask(), {palette: ['10b981'], opacity: 0.35}, '4. Usable Flat Land in 5km (Emerald Green)', true);
Map.addLayer(buf5k.style({color: 'F59E0B', width: 1.5, fillColor: '00000000'}), {}, '5. Outer 3-5 km Ring Limit (Amber)', true);
Map.addLayer(buf3k.style({color: '06B6D4', width: 2, fillColor: '00000000'}), {}, '6. Inner 0-3 km Prime Zone (Cyan)', true);
Map.addLayer(substations, {color: 'FFD700'}, '7. TGTRANSCO Substations (391 Gold Pins)', true);

// 6. Interactive Inspector & Substation Zoom UI
var panel = ui.Panel({
  layout: ui.Panel.Layout.flow('vertical'),
  style: {position: 'top-right', padding: '12px', width: '330px', backgroundColor: '#0f172a'}
});

panel.add(ui.Label({
  value: 'SuryaGrid Land Suitability',
  style: {fontSize: '15px', fontWeight: 'bold', color: '#38bdf8', backgroundColor: '#0f172a'}
}));

panel.add(ui.Label({
  value: 'Strictly Masked to Telangana State & 5 km Radius.',
  style: {fontSize: '11px', color: '#94a3b8', backgroundColor: '#0f172a'}
}));

// Quick Zoom Dropdown to inspect 5km buffer at high resolution
var ssList = [
  'Medaram (400KV)', 'Gajwel (400KV)', 'Dichpally (400KV)',
  'Ramadugu(220KV)', 'Malkaram (220KV)', 'Kondapaka',
  'Thimmajipet', 'Asupaka', 'Narayanguda'
];

var selectSS = ui.Select({
  items: ssList,
  placeholder: '🔍 Zoom to 5km Substation Detail...',
  style: {margin: '8px 0 4px 0', width: '300px'},
  onChange: function(name) {
    var target = substations.filter(ee.Filter.eq('substation_name', name)).first();
    target.geometry().evaluate(function(geom) {
      if (geom) {
        Map.centerObject(ee.Geometry(geom), 13);
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

// Click Inspector for any point or substation
Map.onClick(function(coords) {
  resultBox.clear();
  resultBox.add(ui.Label({
    value: 'Analyzing 0-3km & 3-5km terrain...',
    style: {color: '#facc15', fontSize: '11px', backgroundColor: '#1e293b'}
  }));

  var pt = ee.Geometry.Point([coords.lon, coords.lat]);
  var b3 = pt.buffer(3000);
  var b5 = pt.buffer(5000).difference(b3);

  var areaHa = ee.Image.pixelArea().divide(10000.0);
  var s3 = areaHa.reduceRegion(ee.Reducer.sum(), b3, 60).get('area');
  var u3 = areaHa.updateMask(usable).reduceRegion(ee.Reducer.sum(), b3, 60).get('area');
  var w3 = areaHa.updateMask(water).reduceRegion(ee.Reducer.sum(), b3, 60).get('area');
  var bld3 = areaHa.updateMask(built).reduceRegion(ee.Reducer.sum(), b3, 60).get('area');
  var stp3 = areaHa.updateMask(steep).reduceRegion(ee.Reducer.sum(), b3, 60).get('area');

  var s5 = areaHa.reduceRegion(ee.Reducer.sum(), b5, 60).get('area');
  var u5 = areaHa.updateMask(usable).reduceRegion(ee.Reducer.sum(), b5, 60).get('area');
  var w5 = areaHa.updateMask(water).reduceRegion(ee.Reducer.sum(), b5, 60).get('area');
  var bld5 = areaHa.updateMask(built).reduceRegion(ee.Reducer.sum(), b5, 60).get('area');
  var stp5 = areaHa.updateMask(steep).reduceRegion(ee.Reducer.sum(), b5, 60).get('area');

  ee.Dictionary({
    tot3: s3, use3: u3, wat3: w3, bld3: bld3, stp3: stp3,
    tot5: s5, use5: u5, wat5: w5, bld5: bld5, stp5: stp5
  }).evaluate(function(res) {
    resultBox.clear();
    if (!res) {
      resultBox.add(ui.Label({
        value: 'Error computing statistics.',
        style: {color: '#ef4444', backgroundColor: '#1e293b'}
      }));
      return;
    }

    var pct3 = ((res.use3 || 0) / (res.tot3 || 1)) * 100;
    var pct5 = ((res.use5 || 0) / (res.tot5 || 1)) * 100;
    var wat3_pct = ((res.wat3 || 0) / (res.tot3 || 1)) * 100;
    var bld3_pct = ((res.bld3 || 0) / (res.tot3 || 1)) * 100;
    var stp3_pct = ((res.stp3 || 0) / (res.tot3 || 1)) * 100;

    var v3 = pct3 >= 70 ? 'CLEAR / HIGHLY SUITABLE' : (pct3 >= 40 ? 'MODERATE CLEARANCE' : 'CONSTRAINED');
    var v5 = pct5 >= 70 ? 'CLEAR / HIGHLY SUITABLE' : (pct5 >= 40 ? 'MODERATE CLEARANCE' : 'CONSTRAINED');
    var c3 = pct3 >= 70 ? '#22c55e' : (pct3 >= 40 ? '#f59e0b' : '#ef4444');
    var c5 = pct5 >= 70 ? '#22c55e' : (pct5 >= 40 ? '#f59e0b' : '#ef4444');

    resultBox.add(ui.Label({
      value: 'Location: ' + coords.lat.toFixed(4) + ', ' + coords.lon.toFixed(4),
      style: {color: '#38bdf8', fontSize: '11px', fontWeight: 'bold', backgroundColor: '#1e293b'}
    }));

    resultBox.add(ui.Label({
      value: '0-3 km: ' + v3,
      style: {color: c3, fontWeight: 'bold', fontSize: '12px', margin: '4px 0 2px 0', backgroundColor: '#1e293b'}
    }));
    resultBox.add(ui.Label({
      value: '- Usable Land: ' + (res.use3 || 0).toFixed(0) + ' ha (' + pct3.toFixed(1) + '%)',
      style: {color: '#f8fafc', fontSize: '11px', backgroundColor: '#1e293b'}
    }));
    resultBox.add(ui.Label({
      value: '- Lakes: ' + wat3_pct.toFixed(1) + '% | Built: ' + bld3_pct.toFixed(1) + '% | Slope >5deg: ' + stp3_pct.toFixed(1) + '%',
      style: {color: '#94a3b8', fontSize: '10px', backgroundColor: '#1e293b'}
    }));

    resultBox.add(ui.Label({
      value: '3-5 km: ' + v5,
      style: {color: c5, fontWeight: 'bold', fontSize: '12px', margin: '6px 0 2px 0', backgroundColor: '#1e293b'}
    }));
    resultBox.add(ui.Label({
      value: '- Usable Land: ' + (res.use5 || 0).toFixed(0) + ' ha (' + pct5.toFixed(1) + '%)',
      style: {color: '#f8fafc', fontSize: '11px', backgroundColor: '#1e293b'}
    }));
  });
});
