# BHIV vNEXT: MASTERDB-GEO-QUEST-01 — BLOCKERS & OPEN QUESTIONS REGISTER

**Task:** MASTERDB-GEO-QUEST-01 ("The Geo Quest")  
**Engineers:** Sanskar (Lead), Shravani, Harsha  
**Role:** BHIV-owned geospatial capability discovery, validation, registration, and reuse  
**Last Updated:** October 17, 2026  

---

## 1. Running Open Questions

| # | Question | Impact Area | Current Working Assumption | Status |
| :-: | :--- | :--- | :--- | :-: |
| **Q1** | What is the exact upstream remote repository URL, commit SHA, and branch for the original external God's Eye View prototype (if hosted externally)? | CP1 Revision Record | We baseline against the inspected, validated local reference implementation codified in `/media/ubuntu/New Volume/project/VANA/backend/SPATIAL_GIS_GODS_EYE_VIEW_INTEGRATION.md` and `vana_spatial_engine.py` (Local Git Commit: `fad2ade` / `40d918e`). Upstream remote URL flagged as `<PENDING SANSKAR/HARSHA INPUT>`. | **OPEN (WORKING ON ASSUMPTION)** |
| **Q2** | What are the exact write credentials, JWT roles, and authority boundaries for the canonical MASTERDB Capability Registry write? | CP4 Registration | In strict compliance with Hard Constraint 6: Shravani and Harsha are contributors/validators, NOT the canonical owner. Owner marked as `PENDING MASTERDB AUTHORITY`. Payloads will be prepared in full, but no canonical write will be executed until explicitly confirmed. | **BLOCKED BY DESIGN (PENDING MASTERDB AUTHORITY)** |
| **Q3** | What are the target consumer API endpoints for Bharat Mala and VANA/FIN? | CP5 & CP6 Testing & Delivery | In accordance with the MANTRA → TANTRA → MASTERDB architecture, Bharat Mala and VANA/FIN consume capabilities via TANTRA (`cap.masterdb.geospatial_viewport_query`), avoiding any direct database connection. | **RESOLVED (VIA TANTRA RUNTIME CONTRACT)** |
| **Q4** | What MDU canonical schema references govern geospatial bounding boxes and vector polygons? | CP3 Connection Design | MDU canonical schema `mdu://ontology/geospatial/v1.0/geojson_layer.schema.json` and `mdu://ontology/geospatial/v1.0/bounding_box.schema.json` defined in coordination with Nupur (MDU). | **RESOLVED** |

---

## 2. Active Assumptions

1. **God's Eye View Isolation:** God's Eye View is strictly treated as an external visualizer reference/source. No runtime daemon, package, or container from God's Eye View will be imported as a runtime dependency for Bharat Mala, VANA/FIN, or MasterDB.
2. **Three-Layer Separation:**
   - **SOURCE:** External GIS Surveys / God's Eye View Layer Definitions / Satellite Basemaps.
   - **DATASET:** Governed GeoJSON Spatial Layers (`DS-GEO-TCFS-SANCTUARY-BOUNDARY`, `DS-GEO-MANGROVE-DENSITY-ZONES`, `DS-GEO-MAHARASHTRA-FOREST-DIVISIONS`, `DS-GEO-COASTAL-NURSERIES-ROPVATIKA`).
   - **CAPABILITY:** Reusable Geospatial Capability (`cap.masterdb.geospatial_viewport_query`, `cap.masterdb.geojson_layer_retrieval`).
3. **No Duplicate GIS Databases:** All spatial features are registered in MASTERDB and exposed via TANTRA, eliminating parallel GIS silos in Bharat Mala or VANA/FIN.

---

## 3. Active Blockers

* **None currently blocking CP1 inspection.** Proceeding with CP1 source exploration, capability candidate classification, and licence/provenance audit.
