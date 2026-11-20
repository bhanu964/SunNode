// =========================================================================
// SuryaGrid: Telangana Statewide Electrical Substation Intelligence Platform
// Google Cloud Project: ai-voice-agent-crm
// =========================================================================

// 1. Asset Directory & Assets
var p = 'projects/ai-voice-agent-crm/assets/';
var boundary = ee.FeatureCollection(p + 'suryagrid_telangana_boundary');
var tgracOfficial = ee.FeatureCollection(p + 'suryagrid_tgrac_tgtransco_official');
var masterInventory = ee.FeatureCollection(p + 'suryagrid_tel_statewide_inventory_v2');
var verifiedPDF = ee.FeatureCollection(p + 'suryagrid_substations_verified');

// 2. Map Configuration & Viewport
Map.centerObject(boundary, 7);
Map.setOptions('HYBRID');

// -------------------------------------------------------------------------
// SEPARATE MAP LAYERS
// -------------------------------------------------------------------------

// Layer 1: Telangana State Boundary (Outline)
var empty = ee.Image().byte();
var boundaryOutline = empty.paint({
  featureCollection: boundary,
  color: 1,
  width: 2.5
});
Map.addLayer(boundaryOutline, {palette: ['#F97316']}, '1. Telangana State Boundary (Orange)', true);

// Layer 2: Official TGRAC / TGTRANSCO Grid Substations
Map.addLayer(tgracOfficial, {color: '#F59E0B'}, '⭐ 2. TGRAC TGTRANSCO Official (Gold)', true);

// Layer 3: Extra High Voltage (EHV) Transmission Facilities (400 & 765 kV)
var ehv_400_765 = masterInventory.filter(
  ee.Filter.or(
    ee.Filter.stringContains('voltage_level', '765'),
    ee.Filter.stringContains('voltage_level', '400')
  )
);
Map.addLayer(ehv_400_765, {color: '#DC2626'}, '3. 765 kV & 400 kV EHV Substations (Red)', true);

// Layer 4: 220 kV High Voltage Transmission Substations
var hv_220 = masterInventory.filter(ee.Filter.stringContains('voltage_level', '220'));
Map.addLayer(hv_220, {color: '#EA580C'}, '4. 220 kV Substations (Orange-Red)', true);

// Layer 5: 132 kV Transmission & Primary Grid Step-down Substations
var hv_132 = masterInventory.filter(ee.Filter.stringContains('voltage_level', '132'));
Map.addLayer(hv_132, {color: '#D97706'}, '5. 132 kV Grid Substations (Amber)', true);

// Layer 6: 33/11 kV Primary Distribution Substations
var dist_33_11 = masterInventory.filter(
  ee.Filter.or(
    ee.Filter.eq('infrastructure_category', '33_11KV_SUBSTATION'),
    ee.Filter.stringContains('voltage_level', '33/11')
  )
);
Map.addLayer(dist_33_11, {color: '#16A34A'}, '6. 33/11 kV Substations (Green)', true);

// Layer 7: Government PDF Matched Locations (Exact & High Confidence)
var govt_matched = masterInventory.filter(
  ee.Filter.inList('pdf_match_status', ['EXACT_MATCH', 'HIGH_CONFIDENCE_LIKELY_MATCH'])
);
Map.addLayer(govt_matched, {color: '#9333EA'}, '7. Govt PDF Matched (Purple)', true);

// Layer 8: Distribution Transformers
var transformers = masterInventory.filter(ee.Filter.eq('infrastructure_category', 'DISTRIBUTION_TRANSFORMER'));
Map.addLayer(transformers, {color: '#0284C7'}, '8. Distribution Transformers (Blue)', false);

// -------------------------------------------------------------------------
// PRINT COUNTS TO CONSOLE
// -------------------------------------------------------------------------
print('⭐ Official TGRAC Substations Count:', tgracOfficial.size());
print('⚡ Statewide Master Inventory Count:', masterInventory.size());
print('📄 Govt PDF Verified Matches Count:', verifiedPDF.size());

// -------------------------------------------------------------------------
// INTERACTIVE CLICK INSPECTOR UI
// -------------------------------------------------------------------------
var inspector = ui.Panel({
  layout: ui.Panel.Layout.flow('vertical'),
  style: {position: 'bottom-right', padding: '10px', width: '320px', backgroundColor: '#0f172a'}
});

inspector.add(ui.Label({
  value: 'SuryaGrid Facility Inspector',
  style: {fontWeight: 'bold', fontSize: '15px', color: '#38BDF8'}
}));

inspector.add(ui.Label({
  value: 'Click on any facility on the map to inspect metadata.',
  style: {fontSize: '12px', color: '#94A3B8'}
}));

Map.add(inspector);

Map.onClick(function(coords) {
  inspector.clear();
  inspector.add(ui.Label({value: 'Querying facility...', style: {color: '#38BDF8'}}));

  var clickPoint = ee.Geometry.Point([coords.lon, coords.lat]);
  var nearbyTgrac = tgracOfficial.filterBounds(clickPoint.buffer(600)).first();
  var nearbyInv = masterInventory.filterBounds(clickPoint.buffer(600)).first();

  nearbyTgrac.evaluate(function(tgracFeat) {
    if (tgracFeat) {
      inspector.clear();
      var p = tgracFeat.properties;
      inspector.add(ui.Label({value: '⭐ ' + p.substation_name, style: {fontWeight: 'bold', fontSize: '14px', color: '#F59E0B'}}));
      inspector.add(ui.Label({value: 'Source: TGRAC / TGTRANSCO (Official Govt)', style: {fontSize: '11px', color: '#10B981'}}));
      inspector.add(ui.Label({value: 'Voltage: ' + p.voltage_level, style: {fontSize: '12px', color: '#FACC15'}}));
      inspector.add(ui.Label({value: 'Capacity: ' + p.total_capacity_mva + ' MVA', style: {fontSize: '12px', color: '#38BDF8'}}));
      inspector.add(ui.Label({value: 'Transformers: ' + p.transformer_configuration, style: {fontSize: '11px', color: '#CBD5E1'}}));
      inspector.add(ui.Label({value: 'Type: ' + p.substation_type + ' (' + p.bus_switchgear_scheme + ')', style: {fontSize: '11px', color: '#E2E8F0'}}));
      inspector.add(ui.Label({value: 'Commissioned: ' + p.commissioning_date, style: {fontSize: '11px', color: '#C084FC'}}));
      inspector.add(ui.Label({value: 'District: ' + p.district + ' | Mandal: ' + p.mandal, style: {fontSize: '12px', color: '#E2E8F0'}}));
      inspector.add(ui.Label({value: 'Coords: ' + p.latitude.toFixed(5) + ', ' + p.longitude.toFixed(5), style: {fontSize: '11px', color: '#94A3B8'}}));
      return;
    }

    nearbyInv.evaluate(function(feature) {
      inspector.clear();
      if (!feature) {
        inspector.add(ui.Label({value: 'No facility found within 600m.', style: {color: '#EF4444'}}));
        return;
      }
      var p = feature.properties;
      inspector.add(ui.Label({value: p.facility_name, style: {fontWeight: 'bold', fontSize: '14px', color: '#FFFFFF'}}));
      inspector.add(ui.Label({value: 'Category: ' + p.infrastructure_category, style: {fontSize: '12px', color: '#38BDF8'}}));
      inspector.add(ui.Label({value: 'Voltage: ' + p.voltage_level, style: {fontSize: '12px', color: '#FACC15'}}));
      inspector.add(ui.Label({value: 'District: ' + p.district + ' | Mandal: ' + p.mandal, style: {fontSize: '12px', color: '#E2E8F0'}}));
      inspector.add(ui.Label({value: 'Coordinates: ' + p.latitude.toFixed(5) + ', ' + p.longitude.toFixed(5), style: {fontSize: '12px', color: '#94A3B8'}}));
      inspector.add(ui.Label({value: 'Operator: ' + (p.discom___operator || 'UNKNOWN'), style: {fontSize: '12px', color: '#CBD5E1'}}));
      inspector.add(ui.Label({value: 'PDF Status: ' + p.pdf_match_status, style: {fontSize: '12px', color: '#C084FC'}}));
      inspector.add(ui.Label({value: 'Verification: ' + p.verification_status, style: {fontSize: '12px', color: '#4ADE80'}}));
    });
  });
});
