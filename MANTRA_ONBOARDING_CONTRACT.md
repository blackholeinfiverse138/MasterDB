# MANTRA APPLICATION ONBOARDING CONTRACT: MASTERDB & TANTRA

**Document Identifier:** MANTRA-ONBOARDING-CONTRACT-V1.0  
**Candidate / Author:** Harsha (Ecosystem Integration & Observability)  
**Collaborators:** Kavy (MASTERDB Platform Lead), Ansh Gupta (Governance), Rajaryan (TANTRA), Nupur (MDU), Siddhesh (Bucket), Vijay (InsightFlow)  
**Target Audience:** All MANTRA Application Developers, Enterprise Partners, and System Integrators  
**Date:** October 2026  

---

## 1. Onboarding Philosophy

A user-facing application in the **MANTRA** ecosystem must never connect directly to MASTERDB via database drivers (`psql`, JDBC, SQLite files, or direct TCP ports). 

Instead, every MANTRA application interacts with MASTERDB capabilities through the standard **BHIV/TANTRA Capability Contract**.

> **"A BHIV application should not need to know where MASTERDB physically stores the data, which database engine is running, or which connector extracted it. It only needs the approved capability contract."**

---

## 2. The 10-Step Onboarding Lifecycle

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        THE 10-STEP MANTRA ONBOARDING LIFECYCLE                         │
├─────────┬────────────────────────────┬─────────────────────────────────────────────────┤
│ Step #  │ Lifecycle Phase            │ Description & Protocol Contract                 │
├─────────┼────────────────────────────┼─────────────────────────────────────────────────┤
│ Step 1  │ Identity Registration      │ Application declares its ID and Domain in TANTRA│
│ Step 2  │ Capability Discovery       │ Query TANTRA discovery broker ("I need X")      │
│ Step 3  │ Contract Understanding     │ Resolve semantic schema & units from MDU        │
│ Step 4  │ Access & Purpose Request   │ Declare intended use & 6-tuple parameters       │
│ Step 5  │ Authorization Token        │ Receive signed TANTRA execution token (TTL 300s)│
│ Step 6  │ Governed Invocation        │ Dispatch execution request through TANTRA Fabric│
│ Step 7  │ Data Retrieval             │ Receive canonical structured payload            │
│ Step 8  │ Provenance & Lineage       │ Receive statutory/scientific citation & origin  │
│ Step 9  │ Telemetry Emission         │ Emit W3C traceparent to InsightFlow             │
│ Step 10 │ Evidence Ledger Recording  │ Commit SHA-256 state hash block to Bucket       │
└─────────┴────────────────────────────┴─────────────────────────────────────────────────┘
```

---

## 3. Concrete Onboarding Example: "I Need Mangrove Monitoring Data"

### Step 1: Self-Identification
```json
{
  "actor_id": "MASTERDB_TEST_CONSUMER",
  "domain": "ENVIRONMENT",
  "role": "APPROVED_CONSUMER",
  "service_type": "MANTRA_ANALYTICS_APP"
}
```

### Step 2: Capability Discovery
**Request to TANTRA:**
`GET /tantra/capabilities/discover?query=Mangrove+Monitoring+Data`

**Response from TANTRA:**
```json
{
  "capabilities": [
    {
      "capability_name": "cap.masterdb.mangrove_biomass_retrieval",
      "description": "Retrieve Thane Creek peer-reviewed mangrove blue carbon above-ground biomass",
      "target_dataset_id": "DS-THANECREEK-2023-BIOMASS",
      "domain": "ENVIRONMENT",
      "required_role": "APPROVED_CONSUMER",
      "mdu_schema_ref": "mdu://ontology/environmental/v2.2/biomass.schema.json",
      "supported_actions": ["READ"]
    }
  ]
}
```

### Step 3: Understanding Contract (MDU Semantic Resolution)
**Request to MDU:**
`GET /mdu/schemas/resolve?ref=mdu://ontology/environmental/v2.2/biomass.schema.json`

**Response from MDU:**
```json
{
  "name": "Mangrove Above-Ground Biomass Schema",
  "version": "2.2.0",
  "domain": "ENVIRONMENT",
  "units": {
    "above_ground_biomass": "Mg/ha",
    "canopy_height": "m"
  },
  "fields": {
    "location_name": {"type": "string", "meaning": "Specific wetland or sanctuary plot"},
    "measured_agb_mg_per_ha": {"type": "float", "meaning": "Ground truth allometric plot sample"},
    "estimated_agb_mg_per_ha": {"type": "float", "meaning": "Calibrated satellite inversion estimate"}
  }
}
```

### Step 4 & 5: Access Request & Authorization Token Issuance
**Request to TANTRA Authority:**
```json
{
  "actor_id": "MASTERDB_TEST_CONSUMER",
  "capability_name": "cap.masterdb.mangrove_biomass_retrieval",
  "declared_purpose": "INDEPENDENT_RESEARCH_VALIDATION",
  "action": "READ"
}
```

**Token Issued by TANTRA / Ansh Governance Gate:**
```json
{
  "status": "AUTHORIZED",
  "access_token": {
    "token_id": "0bcac2b6-49a7-473d-82d2-8b3858cfa991",
    "actor_id": "MASTERDB_TEST_CONSUMER",
    "capability_name": "cap.masterdb.mangrove_biomass_retrieval",
    "dataset_id": "DS-THANECREEK-2023-BIOMASS",
    "purpose": "INDEPENDENT_RESEARCH_VALIDATION",
    "mdu_schema_ref": "mdu://ontology/environmental/v2.2/biomass.schema.json",
    "action": "READ",
    "expires_at": 1729088500,
    "token_signature": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  }
}
```

### Step 6, 7 & 8: Governed Execution, Data & Provenance Retrieval
**Execution Payload Delivered by MASTERDB via TANTRA:**
```json
{
  "status": "SUCCESS",
  "data": [
    {
      "record_id": "TC-BIOMASS-001",
      "location_name": "Thane Creek Flamingo Sanctuary (TCFS)",
      "measured_agb_mg_per_ha": 84.83,
      "estimated_agb_mg_per_ha": 111.31,
      "target_species": "Avicennia marina",
      "citation": "DOI: 10.1016/j.ecolind.2023.109876"
    }
  ],
  "metadata": {
    "dataset_id": "DS-THANECREEK-2023-BIOMASS",
    "owner": "ScienceDirect / Elsevier Peer-Reviewed Authors",
    "custodian": "Kavy (MASTERDB Platform Lead)",
    "classification": "CANONICAL_ECOSYSTEM",
    "sensitivity": "SCIENTIFIC_PUBLIC_RESTRICTED"
  }
}
```

### Step 9 & 10: Telemetry (InsightFlow) & Evidence (Bucket)
* **InsightFlow Traceparent:** `00-7cd751b16a714f78b87e1a4d0181d657-ab5d66ab955a4b10-01`
* **Bucket Evidence Block Hash:** `feb9b757d20d03af77bfbfbbe4445b83aa552bc3dfdffb3f192a6d974933b8a9`

---

## 4. Summary of Developer Constraints

1. **No Bespoke Pipelines:** Do not write custom ETL scripts to extract data into local CSV or SQLite copies.
2. **Mandatory Purpose Declaration:** Requests lacking an explicit, approved purpose header (`X-Purpose`) will be rejected with `HTTP 403 FORBIDDEN`.
3. **MDU Schema Adherence:** All consumed data must conform to the MDU registered units and types.
4. **Telemetry & Evidence Loop:** Every retrieval automatically emits a W3C trace to InsightFlow and logs an evidence block in Bucket.
