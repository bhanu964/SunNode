// ==============================================================================
// SuryaGrid: Challenge 10 - Refined 1 km Substation Land Suitability Engine
// Production-Grade Acreage-Calibrated Google Earth Engine Script
// Google Cloud Project: ai-voice-agent-crm
// Scope: Single 1,000m (1 km) Feeder Radius | 10m Dynamic World V1 + USGS SRTM 30m
// ==============================================================================

// 1. Reset Map & Load Official Cloud Assets
Map.clear();
Map.setOptions('HYBRID');

var p = 'projects/ai-voice-agent-crm/assets/';
var boundary = ee.FeatureCollection(p + 'suryagrid_telangana_boundary');
var substations = ee.FeatureCollection(p + 'suryagrid_tgrac_tgtransco_official');

Map.centerObject(boundary, 7);

// 2. High-Resolution Terrain & Slope (USGS SRTM 30m) - Strictly Clipped to Telangana
var dem = ee.Image('USGS/SRTMGL1_003').clip(boundary);
var slope = ee.Terrain.slope(dem);
var flat = slope.lte(5); // <= 5 deg slope (ideal for ground-mounted solar)
var modSlope = slope.gt(5).and(slope.lte(10)); // 5 to 10 deg (moderate slope, minor grading required)
var steep = slope.gt(10); // > 10 deg slope (strictly excluded)

// 3. Generate Single 1,000m (1 km) Feeder Analysis Buffers (~776 acres / ~3.14 km2)
var make1k = function(f) {
  return f.setGeometry(f.geometry().buffer(1000));
};
var buf1k = substations.map(make1k);

// 4. Dynamic World V1 (10m) 12-Month Mode Composite
// MASKED STRICTLY TO 1 KM SUBSTATION BUFFERS (Guarantees zero external/ocean bleed)
var dw = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
  .filterBounds(boundary)
  .filterDate('2023-01-01', '2024-01-01')
  .select('label');

var dwMode = dw.reduce(ee.Reducer.mode()).clip(buf1k);

// Dynamic World Labels:
// 0: water, 1: trees, 2: grass, 3: flooded_vegetation, 4: crops,
// 5: shrub_and_scrub, 6: built, 7: bare, 8: snow_and_ice
var water = dwMode.eq(0).or(dwMode.eq(3));
var water30m = water.focalMax(30, 'circle', 'meters'); // 30m FTL lake/tank buffer
var built = dwMode.eq(6);
var snow = dwMode.eq(8);
var trees = dwMode.eq(1);
var crops = dwMode.eq(4);

// Primary Usable Land: Bare, scrub, grass, AND open farmland / fallow fields (crops)
var primaryLand = dwMode.eq(7).or(dwMode.eq(5)).or(dwMode.eq(2)).or(dwMode.eq(4));

// ==============================================================================
// REVISED 3-TIER OPERATIONAL CLASSIFICATION (45% Opacity Overlays):
// • GREEN (Primary Usable / Ready for Solar):
//   Bare, scrub, grass, AND crops (open farmland) with slope <= 5 deg, outside water30m & built
// • YELLOW (Minor Clearance / Light Grading Only — NEVER for open farmland):
//   Trees (orchards/tree cover) with slope <= 10 deg, OR moderate slope (5°–10°) on non-built/non-water land
// • RED (Strictly Excluded / Hard Blockers):
//   Built-up (substation/urban), water + 30m FTL, flooded veg, snow, or steep slope > 10 deg
// ==============================================================================
var green = primaryLand.and(flat).and(water30m.not()).and(built.not());

var yellowTrees = trees.and(slope.lte(10)).and(water30m.not()).and(built.not());
var yellowSlope = modSlope.and(water30m.not()).and(built.not()).and(snow.not());
var yellow = (yellowTrees.or(yellowSlope)).and(green.not());

var red = built.or(water30m).or(snow).or(steep);

// Morphological Contiguous Filters across updated Green mask:
// 25m radius opening isolates solid contiguous blocks >= 4 acres (~16,187 m2)
// 45m radius opening isolates solid contiguous blocks >= 10 acres (~40,469 m2)
var green4ac = green.focalMin(25, 'circle', 'meters').focalMax(25, 'circle', 'meters');
var green10ac = green.focalMin(45, 'circle', 'meters').focalMax(45, 'circle', 'meters');
var gy4ac = (green.or(yellow)).focalMin(25, 'circle', 'meters').focalMax(25, 'circle', 'meters');

// ==============================================================================
// 5. CLEAN, HIGH-CONTRAST MAP VISUALIZATION
// ==============================================================================
// Layer 1: Telangana State Boundary (Crisp Amber/Orange)
Map.addLayer(boundary.style({color: 'F97316', width: 2, fillColor: '00000000'}), {}, '1. Telangana State Boundary', true);

// Layer 2: 1 km Radius Buffer (Light translucent sky-blue fill #93C5FD at 14% opacity + thin border #60A5FA)
var bufFill = ee.Image().paint(buf1k, 1).visualize({palette: ['93C5FD'], opacity: 0.14});
var bufOutline = ee.Image().paint(buf1k, 1, 1.5).visualize({palette: ['60A5FA']});
Map.addLayer(bufFill, {}, '2. 1 km Feeder Analysis Zone (Light Blue Fill)', true);
Map.addLayer(bufOutline, {}, '3. 1 km Feeder Radius Ring (Soft Blue Border)', true);

// Layer 3: Land-Cover Overlays (45% Opacity)
Map.addLayer(red.selfMask(), {palette: ['EF4444'], opacity: 0.45}, '4. RED: Strictly Excluded (Built/Water+30m/Slope>10deg)', true);
Map.addLayer(yellow.selfMask(), {palette: ['FACC15'], opacity: 0.45}, '5. YELLOW: Trees / Moderate Slope 5-10deg (Minor Clearance)', true);
Map.addLayer(green.selfMask(), {palette: ['22C55E'], opacity: 0.45}, '6. GREEN: Usable Open / Farmland (Bare/Scrub/Grass/Crops <=5deg)', true);
Map.addLayer(green4ac.selfMask(), {palette: ['15803D'], opacity: 0.85}, '7. GREEN CORE: Contiguous >= 4 Acres (Ready)', true);

// Layer 4: High-Contrast Substation Markers (Top Layer)
// 2px White (#FFFFFF) Outer Halo + Dark Charcoal/Navy (#0F172A) Inner Core
var ssHalo = substations.style({color: 'FFFFFF', pointSize: 8, width: 2});
var ssCore = substations.style({color: '0F172A', pointSize: 5, width: 1});
Map.addLayer(ssHalo, {}, '8. Substation Markers (White Halo)', true);
Map.addLayer(ssCore, {}, '9. Substation Core (Charcoal / Navy #0F172A)', true);

// ==============================================================================
// 6. INTERACTIVE DASHBOARD & CLICK INSPECTOR
// ==============================================================================
var panel = ui.Panel({
  layout: ui.Panel.Layout.flow('vertical'),
  style: {
    position: 'top-right',
    padding: '14px',
    width: '360px',
    backgroundColor: '#0F172A',
    border: '1px solid #334155'
  }
});

panel.add(ui.Label({
  value: 'SuryaGrid: 1 km Land Suitability',
  style: {fontSize: '15px', fontWeight: 'bold', color: '#38BDF8', backgroundColor: '#0F172A', margin: '0 0 4px 0'}
}));

panel.add(ui.Label({
  value: 'Challenge 10 | 1 km Radius (~776 ac) | Farmland Ready for Solar',
  style: {fontSize: '11px', color: '#94A3B8', backgroundColor: '#0F172A', margin: '0 0 10px 0'}
}));

// Quick-Zoom Dropdown
var sampleOptions = [
  'Select Substation to Zoom...',
  'K.M.Pally (220KV) - Score: 100 (Rural Prime)',
  'Gajwel (400KV) - Score: 100 (Farmland Ready)',
  'Ganeshpahad - Score: 100 (Industrial/Rural)',
  'Kondapaka - Score: 100 (Farmland Ready)',
  'Narayanguda - Score: 0 (Urban Constrained)',
  'Medaram (400KV)',
  'Dichpally (400KV)',
  'Ramadugu(220KV)',
  'Malkaram (220KV)'
];

var selectSubstation = ui.Select({
  items: sampleOptions,
  placeholder: 'Quick-Zoom to Substation...',
  onChange: function(selected) {
    if (selected === 'Select Substation to Zoom...') return;
    var name = selected.split(' - ')[0];
    var match = substations.filter(ee.Filter.eq('substation_name', name));
    match.size().evaluate(function(count) {
      if (count > 0) {
        Map.centerObject(match.first(), 15);
        inspectSubstation(match.first());
      }
    });
  },
  style: {width: '100%', backgroundColor: '#1E293B', color: '#0F172A', margin: '0 0 10px 0'}
});
panel.add(selectSubstation);

var resultBox = ui.Panel({
  layout: ui.Panel.Layout.flow('vertical'),
  style: {backgroundColor: '#1E293B', padding: '10px', border: '1px solid #334155'}
});

resultBox.add(ui.Label({
  value: 'Click any substation or map point to evaluate 1 km solar feasibility.',
  style: {color: '#94A3B8', fontSize: '11px', backgroundColor: '#1E293B'}
}));
panel.add(resultBox);

// Legend UI
var legendBox = ui.Panel({
  layout: ui.Panel.Layout.flow('vertical'),
  style: {backgroundColor: '#0F172A', margin: '10px 0 0 0'}
});

var addLegendRow = function(color, text) {
  var row = ui.Panel({
    layout: ui.Panel.Layout.flow('horizontal'),
    style: {backgroundColor: '#0F172A', margin: '2px 0'}
  });
  row.add(ui.Label({
    value: '',
    style: {backgroundColor: color, padding: '6px', margin: '2px 8px 0 0', border: '1px solid #475569'}
  }));
  row.add(ui.Label({
    value: text,
    style: {color: '#F8FAFC', fontSize: '11px', backgroundColor: '#0F172A'}
  }));
  legendBox.add(row);
};

legendBox.add(ui.Label({
  value: 'Legend & Operational Zones:',
  style: {color: '#38BDF8', fontSize: '12px', fontWeight: 'bold', backgroundColor: '#0F172A', margin: '4px 0'}
}));
addLegendRow('#15803D', 'Green Core: Contiguous >= 4 Acres (Ready)');
addLegendRow('#22C55E', 'Green: Usable Open / Farmland (Bare, Scrub, Grass, Crops; Slope <= 5°)');
addLegendRow('#FACC15', 'Yellow: Trees / Moderate Slope (5°–10°) — Minor Clearance');
addLegendRow('#EF4444', 'Red: Built-up / Water + 30m / Steep Slope (> 10°)');
addLegendRow('#93C5FD', 'Light Blue: 1 km Feeder Evacuation Zone');
addLegendRow('#0F172A', 'Charcoal + Halo: Substation Point');

panel.add(legendBox);
ui.root.add(panel);

// 10. Inspection Logic - 4-Layer Master Techno-Economic Profile
var ANNEXURE_D_JS = {
  'shankarpally': 450.0, 'veltoor': 355.0, 'medchal': 254.0, 'shapurnagar': 209.0, 'shadnagar': 204.0,
  'yeddumailaram': 200.0, 'miryalaguda': 200.0, 'wanaparthy': 171.0, 'minpur': 165.0, 'kmpally': 158.0,
  'dichpally': 143.0, 'waddekothapally': 143.0, 'tandur': 138.0, 'nirmal': 134.0, 'bheemgal': 134.0,
  'kamareddy': 134.0, 'sadasivapet': 114.0, 'bhongir': 113.0, 'shamshabad': 111.0, 'siddipet': 95.0,
  'jagityal': 95.0, 'miyapur': 86.0, 'fabcity': 71.0, 'rcpuram': 70.0, 'bollaram': 69.0,
  'suryapet': 65.0, 'kothur': 62.0, 'khammam': 62.0, 'warangal': 62.0, 'balanagar': 51.0,
  'nalgonda': 49.0, 'mandamarri': 48.0, 'ibrahimpatnam': 48.0, 'mahabubnagar': 47.0, 'ayyagaripally': 46.0,
  'ramannapeta': 45.0, 'sircilla': 43.0, 'chegunta': 42.5, 'maddur': 39.0, 'pashamailaram': 39.0,
  'karimnagar': 39.0, 'nizamabad': 39.0, 'nandipet': 39.0, 'jakora': 39.0, 'nekkonda': 39.0,
  'wardhannapeta': 39.0, 'gummadidala': 38.71, 'bibinagar': 38.0, 'kolanpaka': 38.0, 'alair': 38.0,
  'gajwel': 38.0, 'shaligowraram': 37.0, 'gadwal': 37.0, 'manoharabad': 33.71, 'tukkapur': 33.0,
  'kandi': 33.0, 'turkayamjal': 32.0, 'durshed': 31.0, 'puttapahad': 30.0, 'adilabad': 30.0,
  'bhainsa': 30.0, 'jammikunta': 30.0, 'husnabad': 30.0, 'pochampad': 30.0, 'geesukonda': 30.0,
  'ghanpur': 30.0, 'raghunathpally': 30.0, 'waddepally': 30.0, 'nagarkurnool': 29.0, 'musthyal': 29.0,
  'thungathurthy': 28.0, 'medak': 28.0, 'kodad': 27.0, 'dharmasagar': 26.0, 'mattampally': 25.0,
  'achampet': 25.0, 'kalwakurthy': 25.0, 'mancherial': 25.0, 'domakonda': 25.0, 'narsapur': 24.0,
  'aitipamula': 23.0, 'guntipally': 23.0, 'kanagal': 23.0, 'wadapally': 23.0, 'ieeza': 23.0,
  'bellampally': 23.0, 'yellandu': 23.0, 'bhadrachalam': 23.0, 'tallada': 23.0, 'manthani': 23.0,
  'rtsb': 23.0, 'pudur': 23.0, 'huzurabad': 23.0, 'mallaram': 23.0, 'kamalapur': 23.0,
  'renjal': 23.0, 'armoor': 23.0, 'morthad': 23.0, 'sirikonda': 23.0, 'lingampet': 23.0,
  'banswada': 23.0, 'nizamsagar': 23.0, 'padmajiwadi': 23.0, 'chelpur': 23.0, 'jangaon': 23.0,
  'mulugu': 23.0, 'narsampet': 23.0, 'alampur': 22.56, 'choutuppal': 22.0, 'haliya': 20.0,
  'ellanthakunta': 19.0, 'yellareddypeta': 19.0, 'mothkur': 18.0, 'parigi': 18.0, 'makthal': 18.0,
  'kowdipally': 18.0, 'penubally': 18.0, 'singur': 16.0, 'polepally': 15.0, 'thirumalaiapally': 15.0,
  'chinnamaroor': 15.0, 'ichoda': 15.0, 'luxettipeta': 15.0, 'mudhole': 15.0, 'sirpurkagaznagar': 15.0,
  'bgangaram': 15.0, 'madhira': 15.0, 'kusumanchi': 15.0, 'manuguru': 15.0, 'kataram': 15.0,
  'korutla': 15.0, 'dharmaram': 15.0, 'dharmapuri': 15.0, 'shanigaram': 15.0, 'kalvasrirampur': 15.0,
  'bodhan': 15.0, 'reddypet': 15.0, 'bichkunda': 15.0, 'chityala': 15.0, 'peddanagaram': 15.0,
  'bhiknoor': 14.0, 'dirsincherla': 13.0, 'kodangal': 13.0, 'zaheerabad': 13.0, 'suglampally': 13.0,
  'narketpally': 12.0, 'amangal': 11.0, 'godur': 11.0, 'madgulapally': 10.0, 'ramayampet': 10.0,
  'chennur': 10.0, 'manakondur': 10.0, 'jogipet': 9.0, 'habsipur': 8.93, 'takkalapally': 8.0,
  'yacharam': 8.0, 'tunkibollaram': 8.0, 'mulkanoor': 8.0, 'aswaraopeta': 6.0, 'narayankhed': 5.0,
  'peddashankarampet': 5.0
};

function inspectSubstation(feat) {
  resultBox.clear();
  resultBox.add(ui.Label({
    value: 'Computing 4-layer master techno-economic profile...',
    style: {color: '#38BDF8', fontSize: '11px', backgroundColor: '#1E293B'}
  }));

  var pt = feat.geometry();
  var b1k = pt.buffer(1000);

  var pxAc = ee.Image.pixelArea().multiply(0.000247105);
  var bands = pxAc.rename('tot').addBands([
    pxAc.updateMask(green).rename('grn'),
    pxAc.updateMask(green4ac).rename('g4'),
    pxAc.updateMask(green10ac).rename('g10'),
    pxAc.updateMask(yellow).rename('yel'),
    pxAc.updateMask(gy4ac).rename('gy4'),
    pxAc.updateMask(red).rename('red')
  ]);

  var stats = bands.reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: b1k,
    scale: 10,
    maxPixels: 1e9
  });

  stats.evaluate(function(val) {
    if (!val) return;
    resultBox.clear();

    var name = feat.get('substation_name').getInfo() || 'Selected Point';
    var dist = feat.get('district').getInfo() || 'Telangana';
    var kv = feat.get('voltage_level').getInfo() || 'Substation';

    var totAc = val.tot || 776.0;
    var grnAc = val.grn || 0.0;
    var g4Ac = val.g4 || 0.0;
    var g10Ac = val.g10 || 0.0;
    var yelAc = val.yel || 0.0;
    var gy4Ac = val.gy4 || 0.0;
    var redAc = val.red || 0.0;
    var redPct = (redAc / totAc * 100.0);

    var meets10 = g10Ac >= 10.0;
    var meets4 = g4Ac >= 4.0;
    var largestGreen = meets10 ? Math.max(10.0, g10Ac) : (meets4 ? Math.max(4.0, g4Ac) : Math.min(3.9, grnAc));
    largestGreen = Math.min(grnAc, largestGreen);

    var landScore = 0;
    var tier = '';
    var tierColor = '#EF4444';

    if (meets10) {
      landScore = Math.min(100.0, 90.0 + Math.min(10.0, (largestGreen - 10.0) * 0.2));
      tier = 'HIGH (>=10 ac Farmland/Open Ready)';
      tierColor = '#22C55E';
    } else if (meets4) {
      landScore = 70.0 + ((largestGreen - 4.0) / 6.0) * 19.0;
      tier = 'VIABLE (4-10 ac Farmland/Open Ready)';
      tierColor = '#38BDF8';
    } else if (gy4Ac >= 4.0) {
      landScore = 40.0 + Math.min(29.0, (gy4Ac / 20.0) * 29.0);
      tier = 'CONDITIONAL (Needs Clearance/Grading)';
      tierColor = '#FACC15';
    } else {
      landScore = Math.max(0.0, 39.0 * (1.0 - redPct / 100.0));
      tier = 'LOW / CONSTRAINED';
      tierColor = '#EF4444';
    }

    var landMw = +(largestGreen / 4.5).toFixed(1);

    // Grid Matching
    var normName = name.toLowerCase().replace(/\(\s*\d+\s*kv\s*\)/g, '').replace(/[^a-z0-9]/g, '');
    var kvStr = (kv + ' ' + name).toLowerCase();
    var is400 = kvStr.indexOf('400') !== -1 || kvStr.indexOf('765') !== -1;
    var is220 = kvStr.indexOf('220') !== -1;

    var gridSpareMw = 28.4;
    var gridBasis = 'Calculated (45% PTR MVA)';

    if (is400 && normName.indexOf('dichpally') !== -1) {
      gridSpareMw = 650.25;
      gridBasis = 'Calculated (45% of 1445 MVA)';
    } else {
      for (var k in ANNEXURE_D_JS) {
        if (k === normName || (k.length >= 5 && normName.indexOf(k) !== -1)) {
          gridSpareMw = ANNEXURE_D_JS[k];
          gridBasis = 'DISCOM Annexure-D Notified';
          break;
        }
      }
    }

    var deployableMw = 0.0;
    var bottleneck = 'LAND / URBAN EXCLUDED (0 MW)';
    if (landMw >= 0.9) {
      if (gridSpareMw < landMw) {
        deployableMw = gridSpareMw;
        bottleneck = 'GRID TRANSFORMER CONSTRAINED';
      } else if (landMw < gridSpareMw) {
        deployableMw = landMw;
        bottleneck = '1 KM LAND RADIUS CONSTRAINED';
      } else {
        deployableMw = landMw;
        bottleneck = 'BALANCED (LAND = GRID)';
      }
    }

    // Voltage-Tier Evacuation & Feeder Bays
    var evacKv = 33;
    var bayType = '33 kV VCB Feeder Bay';
    var evacAmps = +(deployableMw * 17.85).toFixed(1);
    var evacBays = deployableMw > 0 ? Math.ceil(evacAmps / 320.0) : 0;
    var tariffInr = 3.13;
    var tariffTier = 'PM-KUSUM Feeder';

    if (is400 && deployableMw > 30.0) {
      evacKv = 220;
      bayType = '220 kV SF6 Line Bay';
      evacAmps = +(deployableMw * 2.68).toFixed(1);
      evacBays = Math.ceil(deployableMw / 100.0);
      tariffInr = 2.75;
      tariffTier = 'Utility STU (220 kV)';
    } else if (is220 && deployableMw > 30.0) {
      evacKv = 132;
      bayType = '132 kV SF6 Line Bay';
      evacAmps = +(deployableMw * 4.46).toFixed(1);
      evacBays = Math.ceil(deployableMw / 50.0);
      tariffInr = 2.75;
      tariffTier = 'Utility STU (132 kV)';
    }

    // Solar Generation & Financial Model (Tiered Tariff)
    var pvgisEy = 1491151; // Statewide avg kWh/MWp
    var annualMu = +((deployableMw * pvgisEy) / 1e6).toFixed(2);
    var capexCr = +(deployableMw * 3.75).toFixed(2);
    var revCr = +((annualMu * 1e6 * tariffInr) / 1e7).toFixed(2);
    var opexCr = +(deployableMw * 0.065).toFixed(2);
    var ebitdaCr = +(revCr - opexCr).toFixed(2);
    var payback = ebitdaCr > 0 ? +(capexCr / ebitdaCr).toFixed(2) : 0.0;

    // Master Score (150 MW capacity cap)
    var masterScore = 0.0;
    if (deployableMw > 0) {
      var landComp = 0.40 * landScore;
      var gridComp = 0.35 * Math.min(100.0, (deployableMw / 150.0) * 100.0);
      var solarComp = 0.25 * Math.min(100.0, Math.max(0.0, ((pvgisEy - 1500000.0) / 140000.0) * 100.0));
      masterScore = +(landComp + gridComp + solarComp).toFixed(1);
    }

    // Render 4-Layer Profile Panel
    resultBox.add(ui.Label({
      value: name + ' (' + kv + ')',
      style: {fontWeight: 'bold', fontSize: '13px', color: '#F8FAFC', backgroundColor: '#1E293B', margin: '0 0 1px 0'}
    }));
    resultBox.add(ui.Label({
      value: 'District: ' + dist + ' | Master Score: ' + masterScore + ' / 100',
      style: {fontWeight: 'bold', fontSize: '11px', color: '#38BDF8', backgroundColor: '#1E293B', margin: '0 0 6px 0'}
    }));

    // Layer 1: Land
    resultBox.add(ui.Label({
      value: '1. LAND: Contiguous ' + largestGreen.toFixed(1) + ' ac -> ' + landMw + ' MW Potential',
      style: {fontWeight: 'bold', fontSize: '10.5px', color: '#22C55E', backgroundColor: '#1E293B'}
    }));
    resultBox.add(ui.Label({
      value: '   Open/Farmland: ' + grnAc.toFixed(0) + ' ac | Excluded: ' + redAc.toFixed(0) + ' ac (' + redPct.toFixed(1) + '%)',
      style: {fontSize: '9.5px', color: '#94A3B8', backgroundColor: '#1E293B', margin: '0 0 4px 0'}
    }));

    // Layer 2: Grid
    resultBox.add(ui.Label({
      value: '2. GRID: Spare ' + gridSpareMw.toFixed(1) + ' MW (' + gridBasis + ')',
      style: {fontWeight: 'bold', fontSize: '10.5px', color: '#FACC15', backgroundColor: '#1E293B'}
    }));
    resultBox.add(ui.Label({
      value: '   -> True Deployable: ' + deployableMw.toFixed(1) + ' MW [' + bottleneck + ']',
      style: {fontSize: '10px', color: deployableMw > 0 ? '#38BDF8' : '#EF4444', backgroundColor: '#1E293B', fontWeight: 'bold'}
    }));
    resultBox.add(ui.Label({
      value: '   Evacuation: ' + evacAmps + ' A @ ' + evacKv + ' kV (' + evacBays + ' x ' + bayType + ')',
      style: {fontSize: '9.5px', color: '#94A3B8', backgroundColor: '#1E293B', margin: '0 0 4px 0'}
    }));

    // Layer 3: Solar Generation
    resultBox.add(ui.Label({
      value: '3. SOLAR: ' + annualMu + ' MU/yr (@ PVGIS 1,491 kWh/MWp/yr)',
      style: {fontWeight: 'bold', fontSize: '10.5px', color: '#A855F7', backgroundColor: '#1E293B'}
    }));

    // Layer 4: Finance (Tiered Tariff)
    resultBox.add(ui.Label({
      value: '4. ROI: CAPEX ₹' + capexCr + ' Cr | Rev ₹' + revCr + ' Cr/yr (' + tariffTier + ' @ ₹' + tariffInr + ') | Payback ' + payback + ' yrs',
      style: {fontWeight: 'bold', fontSize: '10px', color: '#38BDF8', backgroundColor: '#1E293B', margin: '2px 0 0 0'}
    }));
  });
}

// Map Click Trigger
Map.onClick(function(coords) {
  var clickPt = ee.Geometry.Point([coords.lon, coords.lat]);
  var nearest = substations.filterBounds(clickPt.buffer(3000));
  nearest.size().evaluate(function(cnt) {
    if (cnt > 0) {
      inspectSubstation(nearest.first());
    } else {
      var dummyFeat = ee.Feature(clickPt, {
        substation_name: 'Custom Location',
        district: 'Telangana',
        voltage_level: 'Grid Feeder'
      });
      inspectSubstation(dummyFeat);
    }
  });
});

print('SuryaGrid 1 km Calibrated Engine Loaded Successfully.');
