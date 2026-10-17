#!/usr/bin/env python3
"""
Test Spatial Source Inspection (CP1 Validation Script)
Task: MASTERDB-GEO-QUEST-01
Engineer: Sanskar / Harsha

Validates the inspected God's Eye View reference spatial layers,
verifies topological closure, checks coordinate bounding box ranges,
and extracts canonical sample GeoJSON layers for CP1 evidence.
"""

import json
import os
import sys

# Add VANA backend to path to inspect vana_spatial_engine
vana_backend_path = "/media/ubuntu/New Volume/project/VANA/backend"
if vana_backend_path not in sys.path:
    sys.path.insert(0, vana_backend_path)

from vana_spatial_engine import VanaSpatialEngine


def run_cp1_inspection():
    print("=" * 80)
    print("CP1 SOURCE INSPECTION & GEOSPATIAL VALIDATION HARNESS")
    print("=" * 80)

    engine = VanaSpatialEngine()
    layers = engine.list_layers()
    print(f"Discovered Layers in Spatial Engine: {len(layers)}")
    for l in layers:
        print(f" - Layer ID: {l['layer_id']:<28} | Type: {l['type']:<18} | CRS: {l['crs']}")

    # 1. Test Topological Closure on Polygons
    print("\n[TEST 1] Topological Polygon Closure Check:")
    sanctuary = engine.get_layer("thane_creek_sanctuary")
    coords = sanctuary["geometry"]["coordinates"][0]
    is_closed = coords[0] == coords[-1]
    print(f"  Sanctuary Boundary First Point: {coords[0]}")
    print(f"  Sanctuary Boundary Last Point:  {coords[-1]}")
    print(f"  Topological Closure: {'PASS (Closed)' if is_closed else 'FAIL'}")
    assert is_closed, "Sanctuary polygon is not closed!"

    # 2. Test Mangrove Density Polygons
    density_zones = engine.get_layer("mangrove_density_zones")
    print(f"\n[TEST 2] Mangrove Density Strata ({len(density_zones['features'])} Features):")
    for feat in density_zones["features"]:
        feat_coords = feat["geometry"]["coordinates"][0]
        feat_closed = feat_coords[0] == feat_coords[-1]
        print(f"  Feature '{feat['id']}': {feat['properties']['zone_name']} | Closed: {feat_closed}")
        assert feat_closed, f"Feature {feat['id']} is not closed!"

    # 3. Test Coordinate Envelope (WGS84 EPSG:4326 ranges)
    print("\n[TEST 3] WGS84 Geographic Coordinate Ranges:")
    envelope = engine.get_unified_spatial_envelope()
    all_lons = []
    all_lats = []
    for f in envelope["features"]:
        geom_type = f["geometry"]["type"]
        if geom_type == "Polygon":
            for pt in f["geometry"]["coordinates"][0]:
                all_lons.append(pt[0])
                all_lats.append(pt[1])
        elif geom_type == "Point":
            all_lons.append(f["geometry"]["coordinates"][0])
            all_lats.append(f["geometry"]["coordinates"][1])
        elif geom_type == "LineString":
            for pt in f["geometry"]["coordinates"]:
                all_lons.append(pt[0])
                all_lats.append(pt[1])

    min_lon, max_lon = min(all_lons), max(all_lons)
    min_lat, max_lat = min(all_lats), max(all_lats)
    print(f"  Bounding Box Lon: [{min_lon:.4f}, {max_lon:.4f}]")
    print(f"  Bounding Box Lat: [{min_lat:.4f}, {max_lat:.4f}]")
    assert 68.0 <= min_lon <= max_lon <= 98.0, "Longitudes fall outside India bounding envelope!"
    assert 6.0 <= min_lat <= max_lat <= 38.0, "Latitudes fall outside India bounding envelope!"
    print("  Geographic Bounds: VALID (Enclosed in Indian Territorial Waters & Subcontinent)")

    # 4. Save API Sample
    sample_path = "api_samples/sample_layer_sanctuary.json"
    with open(sample_path, "w") as f:
        json.dump(sanctuary, f, indent=2)
    print(f"\n[ARTIFACT] Exported sample layer to: {sample_path}")

    print("\n" + "=" * 80)
    print("CP1 SOURCE EXPLORATION INSPECTION: 100% PASS")
    print("=" * 80)
    return True


if __name__ == "__main__":
    run_cp1_inspection()
