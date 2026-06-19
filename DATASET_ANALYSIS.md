# Dataset Analysis Report

**File:** `data/jan to may police violation_anonymized791b166.csv`  
**Analysis date:** 2026-06-19  
**Scope:** Exploratory data analysis only — no dashboard or model training.

---

## 1. Executive Summary

This dataset contains **298,450 anonymized parking/traffic violation records** from Bengaluru, India, spanning **2023-11-09 to 2024-04-08** (UTC). Despite the filename referencing “Jan to May,” the data covers **Nov 2023 – Apr 2024**, with **April 2024 partially represented** (~15.4K records vs ~55–66K in other months).

Each row is a single violation event with geolocation, vehicle metadata, violation labels, enforcement device/officer IDs, police station jurisdiction, optional junction name, and a partial validation workflow (approved/rejected).

**Key strengths:** Large volume, complete coordinates, rich categorical labels, geospatial coverage across Bengaluru, unique record IDs, no full-row duplicates.

**Key limitations:** Several columns are 100% null (`description`, `closed_datetime`, `action_taken_timestamp`); validation fields are missing for ~42% of records; junction is unspecified for ~50% of rows; timestamps show a strong batch-processing pattern that may not reflect true violation time; filename/date-range mismatch.

---

## 2. Dataset Overview

| Metric | Value |
|--------|-------|
| Rows | 298,450 |
| Columns | 24 |
| Memory (approx.) | 320.5 MB |
| Unique IDs | 298,450 (no duplicate `id`) |
| Full-row duplicates | 0 |
| Geographic scope | Bengaluru, Karnataka, India |
| Date range (`created_datetime`) | 2023-11-09 → 2024-04-08 |

### Monthly record volume

| Month | Records |
|-------|---------|
| 2023-11 | 43,504 |
| 2023-12 | 63,917 |
| 2024-01 | 65,479 |
| 2024-02 | 54,660 |
| 2024-03 | 55,453 |
| 2024-04 | 15,432 *(partial month)* |

---

## 3. Data Dictionary

| Column | Type | Non-null | Missing % | Unique | Description |
|--------|------|----------|-----------|--------|-------------|
| `id` | string (identifier) | 298,450 | 0.0% | 298,450 | Unique anonymized violation record ID (`FKID` prefix). Primary key. |
| `latitude` | float64 | 298,450 | 0.0% | 177,982 | WGS84 latitude of violation location. |
| `longitude` | float64 | 298,450 | 0.0% | 177,378 | WGS84 longitude of violation location. |
| `location` | string (text) | 295,409 | 1.02% | 10,942 | Human-readable geocoded address. |
| `vehicle_number` | string (identifier) | 298,450 | 0.0% | 231,890 | Anonymized registration number at detection time. |
| `vehicle_type` | categorical | 298,450 | 0.0% | 22 | Vehicle category (CAR, SCOOTER, MOTOR CYCLE, etc.). |
| `description` | float64 | 0 | **100.0%** | 0 | Free-text description — **entirely unused/null**. |
| `violation_type` | categorical (multi-label) | 298,450 | 0.0% | 991 raw strings | JSON-like list of violation labels (e.g. `["NO PARKING"]`). Expands to **27 distinct labels**. |
| `offence_code` | categorical (multi-label) | 298,450 | 0.0% | 991 raw strings | JSON-like list of numeric offence codes aligned to violation types. |
| `created_datetime` | datetime (UTC) | 298,450 | 0.0% | 94,417 | Record creation / detection timestamp (ISO 8601, `+00` offset). |
| `closed_datetime` | float64 | 0 | **100.0%** | 0 | Case closure timestamp — **entirely null**. |
| `modified_datetime` | datetime (UTC) | 298,450 | 0.0% | 298,450 | Last modification timestamp (always populated). |
| `device_id` | string (identifier) | 298,450 | 0.0% | 3,070 | Anonymized enforcement device/camera ID (`FKDEV` prefix). |
| `created_by_id` | string (identifier) | 298,445 | 0.002% | 2,666 | Anonymized officer/system user ID (`FKUSR` prefix). |
| `center_code` | float64 (ordinal/zone) | 287,190 | 3.77% | 52 | Traffic management center / zone code. |
| `police_station` | categorical | 298,445 | 0.002% | 54 | Jurisdiction police station name. |
| `data_sent_to_scita` | boolean | 298,450 | 0.0% | 2 | Whether record was transmitted to SCITA system (`True`: 85.7%). |
| `junction_name` | categorical | 298,445 | 0.002% | 169 | Named junction (`BTP### - ...`) or `No Junction`. |
| `action_taken_timestamp` | float64 | 0 | **100.0%** | 0 | Enforcement action timestamp — **entirely null**. |
| `data_sent_to_scita_timestamp` | datetime (UTC) | 42,161 | 85.87% | 42,161 | SCITA transmission timestamp (sparse). |
| `updated_vehicle_number` | string (identifier) | 173,196 | 41.97% | 143,133 | Post-validation corrected plate number. |
| `updated_vehicle_type` | categorical | 173,196 | 41.97% | 22 | Post-validation corrected vehicle type. |
| `validation_status` | categorical | 173,196 | 41.97% | 5 | Manual review outcome: `approved`, `rejected`, `created1`, `processing`, `duplicate`. |
| `validation_timestamp` | datetime (UTC) | 173,196 | 41.97% | 170,115 | When validation decision was recorded. |

---

## 4. Column Classification

### Categorical
- `vehicle_type`, `updated_vehicle_type`
- `violation_type`, `offence_code` *(multi-label; store as list or one-hot per label)*
- `police_station`, `junction_name`
- `validation_status`
- `data_sent_to_scita` *(boolean, treat as binary categorical)*

### Numerical
- `latitude`, `longitude` *(continuous geospatial coordinates)*
- `center_code` *(numeric zone code; 52 distinct values — use as categorical or embedding)*

### Datetime
- `created_datetime` *(primary event timestamp)*
- `modified_datetime`
- `validation_timestamp`
- `data_sent_to_scita_timestamp`
- `closed_datetime` *(100% null — unusable)*
- `action_taken_timestamp` *(100% null — unusable)*

### Geospatial
- `latitude`, `longitude` — point coordinates
- `location` — geocoded address text (supports geocoding validation, pin-code extraction, neighborhood parsing)

### Identifiers *(features for grouping/aggregation, not direct ML inputs without encoding)*
- `id`, `vehicle_number`, `updated_vehicle_number`, `device_id`, `created_by_id`

### Text
- `location` — semi-structured address strings
- `description` — empty

---

## 5. Data Quality Assessment

### 5.1 Missing Values

| Severity | Columns |
|----------|---------|
| **100% missing** | `description`, `closed_datetime`, `action_taken_timestamp` |
| **>40% missing** | `updated_vehicle_number`, `updated_vehicle_type`, `validation_status`, `validation_timestamp` (41.97%) |
| **>85% missing** | `data_sent_to_scita_timestamp` (85.87%) |
| **Low missing (<4%)** | `center_code` (3.77%), `location` (1.02%) |
| **Negligible** | `created_by_id`, `police_station`, `junction_name` (5 rows each, 0.002%) |
| **Complete** | `id`, coordinates, vehicle fields, violation fields, core timestamps, device IDs |

**Implication:** Any model using validation outcomes can only train on **~58% of records** (173,196 rows). SCITA timing analysis is limited to ~14% of records.

### 5.2 Duplicates

| Check | Result |
|-------|--------|
| Full-row duplicates | 0 |
| Duplicate `id` values | 0 |
| Unique `id` count | 298,450 |

No deduplication required at the record-ID level. Some near-duplicate events exist (same location, time, vehicle type within seconds) but with distinct IDs — likely separate detections or re-captures.

### 5.3 Invalid / Suspicious Coordinates

| Check | Count | Notes |
|-------|-------|-------|
| Missing lat/lon | 0 | Fully populated |
| Out of valid Earth range | 0 | All within ±90/±180 |
| (0, 0) pairs | 0 | None |
| Outside Bengaluru bbox *(lat 12.7–13.2, lon 77.3–77.9)* | **168** | 0.06% — likely edge cases or geocoding errors |

**Coordinate ranges:**
- Latitude: 12.803 → 13.294 (mean 12.981)
- Longitude: 77.443 → 77.772 (mean 77.601)

Coordinates are overwhelmingly valid and centered on Bengaluru urban area.

### 5.4 Inconsistent Categories

| Issue | Details |
|-------|---------|
| **Multi-label violation encoding** | `violation_type` stored as JSON strings with 991 unique raw combinations; only 27 unique labels when exploded. 40,110 records (13.4%) carry multiple violation types. |
| **Vehicle type corrections** | 6,169 records where `vehicle_type` ≠ `updated_vehicle_type` when both present (~3.6% of validated subset). |
| **Validation status values** | Non-standard values: `created1` (7,044), `processing` (678), `duplicate` (320) in addition to `approved` / `rejected`. |
| **Junction placeholder** | 49.55% of records use `No Junction` — limits junction-level modeling. |
| **Police station naming** | 54 unique names; no casing/spelling variants detected at lowercase level. |
| **Filename vs content** | File named “jan to may” but data starts Nov 2023 and ends early Apr 2024. |
| **Timestamp semantics** | Raw hour distribution shows peaks at 04:00–06:00 and 19:00–23:00 (as stored). This bimodal pattern suggests timestamps may reflect **batch ingestion/processing** as much as on-street violation time. Negative `modified − created` deltas exist (min −72 hours). Treat temporal features with caution. |

### 5.5 Offence Code ↔ Violation Type Mapping

Top codes align cleanly with labels:

| Code | Count | Typical label |
|------|-------|---------------|
| 112 | 164,977 | WRONG PARKING |
| 113 | 139,050 | NO PARKING |
| 107 | 23,943 | PARKING IN A MAIN ROAD |
| 116 | 7,848 | DEFECTIVE NUMBER PLATE |
| 105 | 3,757 | PARKING ON FOOTPATH |

---

## 6. Summary Statistics

### Numerical columns

| Statistic | latitude | longitude | center_code |
|-----------|----------|-----------|-------------|
| count | 298,450 | 298,450 | 287,190 |
| mean | 12.981 | 77.601 | 23.02 |
| std | 0.050 | 0.051 | 20.01 |
| min | 12.803 | 77.443 | 2 |
| 25% | 12.963 | 77.571 | 11 |
| 50% | 12.977 | 77.584 | 17 |
| 75% | 12.997 | 77.622 | 29 |
| max | 13.294 | 77.772 | 88 |

### Derived temporal intervals

| Interval | count | mean (hrs) | median (hrs) | max (hrs) |
|----------|-------|------------|--------------|-----------|
| `modified_datetime − created_datetime` | 298,445 | 8.5 | 0.26 | 2,686 |
| `validation_timestamp − created_datetime` | 173,030 | 96.8 | 31.0 | 3,664 |

Validation typically occurs ~1.3 days after creation (median ~31 hours).

---

## 7. Exploratory Findings

### 7.1 Top Police Stations by Violations

| Rank | Police Station | Violations | Share |
|------|----------------|------------|-------|
| 1 | Upparpet | 34,468 | 11.5% |
| 2 | Shivajinagar | 28,044 | 9.4% |
| 3 | Malleshwaram | 22,200 | 7.4% |
| 4 | HAL Old Airport | 20,819 | 7.0% |
| 5 | City Market | 17,646 | 5.9% |
| 6 | Vijayanagara | 14,652 | 4.9% |
| 7 | Rajajinagar | 10,998 | 3.7% |
| 8 | Kodigehalli | 10,916 | 3.7% |
| 9 | Magadi Road | 8,558 | 2.9% |
| 10 | Jeevanbheemanagar | 6,736 | 2.3% |

Top 3 stations account for ~28% of all violations — significant geographic concentration in central Bengaluru.

### 7.2 Top Junctions by Violations
*(excluding `No Junction` — 147,890 records have no junction label)*

| Rank | Junction | Violations |
|------|----------|------------|
| 1 | BTP051 - Safina Plaza Junction | 15,449 |
| 2 | BTP082 - KR Market Junction | 11,538 |
| 3 | BTP040 - Elite Junction | 10,718 |
| 4 | BTP044 - Sagar Theatre Junction | 10,549 |
| 5 | BTP211 - Central Street Junction | 5,388 |
| 6 | BTP058 - Subbanna Junction | 5,189 |
| 7 | BTP027 - Modi Bridge Junction | 4,584 |
| 8 | BTP020 - Hosahalli Metro Station | 4,101 |
| 9 | BTP057 - Anand Rao Junction | 3,935 |
| 10 | BTP080 - NR Road, SP Road Junction | 3,681 |

168 named junctions total; top 10 junctions account for ~58% of junction-tagged violations.

### 7.3 Top Violation Types
*(exploded multi-label counts — totals exceed row count)*

| Rank | Violation Type | Count |
|------|----------------|-------|
| 1 | WRONG PARKING | 164,977 |
| 2 | NO PARKING | 139,050 |
| 3 | PARKING IN A MAIN ROAD | 23,943 |
| 4 | DEFECTIVE NUMBER PLATE | 7,848 |
| 5 | PARKING ON FOOTPATH | 3,757 |
| 6 | PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC | 2,403 |
| 7 | DOUBLE PARKING | 2,037 |
| 8 | PARKING NEAR ROAD CROSSING | 1,687 |
| 9 | REFUSE TO GO FOR HIRE | 887 |
| 10 | PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS | 525 |

Parking-related offences dominate (>95%). 27 distinct violation labels exist; long tail includes rare offences (e.g. `VIOLATING LANE DISIPLINE`: 5).

### 7.4 Top Vehicle Types

| Rank | Vehicle Type | Count | Share |
|------|--------------|-------|-------|
| 1 | SCOOTER | 94,856 | 31.8% |
| 2 | CAR | 88,870 | 29.8% |
| 3 | MOTOR CYCLE | 40,811 | 13.7% |
| 4 | PASSENGER AUTO | 37,813 | 12.7% |
| 5 | MAXI-CAB | 11,372 | 3.8% |
| 6 | LGV | 8,255 | 2.8% |
| 7 | GOODS AUTO | 2,934 | 1.0% |
| 8 | MOPED | 2,199 | 0.7% |
| 9 | PRIVATE BUS | 1,633 | 0.5% |
| 10 | VAN | 1,466 | 0.5% |

Two-wheelers (scooter + motorcycle + moped) ≈ **46%**; four-wheelers (car + maxi-cab) ≈ **34%**.

### 7.5 Hourly Violation Distribution

Distribution depends on timezone interpretation:

**If timestamps are true UTC (converted to IST +5:30):**
- Peak hours: **10:00–11:00 IST** (~32K each)
- Trough: **15:00–19:00 IST** (<1,500 per hour)

**If timestamps are local time mislabeled as UTC (naive reading):**
- Primary peak: **04:00–06:00** (~29–34K) — likely batch processing artifact
- Secondary peak: **19:00–23:00** (~11–23K) — plausible on-street enforcement window

**Recommendation:** Validate timestamp semantics with data provider before building time-of-day models. Prefer `modified_datetime` patterns and cross-check with device deployment schedules.

| Hour (naive) | Count | Hour (naive) | Count |
|--------------|-------|--------------|-------|
| 00 | 21,760 | 12 | 219 |
| 01 | 17,155 | 13 | 56 |
| 02 | 24,770 | 14 | 16 |
| 03 | 25,707 | 15 | 66 |
| 04 | 29,102 | 16 | 416 |
| 05 | 34,085 | 17 | 818 |
| 06 | 26,890 | 18 | 1,971 |
| 07 | 14,608 | 19 | 10,713 |
| 08 | 8,556 | 20 | 11,834 |
| 09 | 3,145 | 21 | 19,763 |
| 10 | 518 | 22 | 22,839 |
| 11 | 577 | 23 | 22,861 |

### 7.6 Weekday Violation Distribution

| Weekday | Violations | Share |
|---------|------------|-------|
| Sunday | 50,160 | 16.8% |
| Saturday | 44,523 | 14.9% |
| Thursday | 43,547 | 14.6% |
| Tuesday | 42,697 | 14.3% |
| Wednesday | 41,974 | 14.1% |
| Friday | 40,864 | 13.7% |
| Monday | 34,680 | 11.6% |

Relatively uniform mid-week; **Sunday highest**, Monday lowest. Difference may reflect enforcement scheduling rather than true violation rates.

---

## 8. ML Problem Feasibility

### 8.1 Realistically Possible ML Problems

| Problem | Type | Feasibility | Rationale |
|---------|------|-------------|-----------|
| **Violation hotspot prediction** | Regression / density estimation | **High** | 298K geo-tagged points; cluster/junction/station aggregations viable. |
| **Violation type classification** | Multi-class / multi-label | **High** | 27 labels; rich features (location, vehicle, time, device). |
| **Vehicle type prediction** | Multi-class | **Medium–High** | 22 classes; imbalanced but sufficient samples per top class. |
| **Validation approval prediction** | Binary classification | **Medium** | 173K labeled records (66% approved, 29% rejected among validated); watch for temporal leakage. |
| **Police station / zone assignment** | Multi-class | **Medium** | 54 stations; strong spatial signal from lat/lon. |
| **Junction identification** | Multi-class | **Medium–Low** | Only 50% have junction labels; 168 classes with long tail. |
| **Demand forecasting (violations per zone/time)** | Time-series | **Medium** | 5+ months of data; need timestamp semantics clarified; April incomplete. |
| **Anomaly / outlier detection** | Unsupervised | **High** | Detect unusual locations, devices, violation combos, validation patterns. |
| **Repeat offender detection** | Graph / clustering | **Medium** | 231K unique anonymized plates; can aggregate per vehicle. |
| **SCITA transmission prediction** | Binary classification | **Medium** | 85.7% True — imbalanced; features from location/device/type. |

### 8.2 Targets That CAN Be Predicted

| Target | Notes |
|--------|-------|
| `violation_type` (single or multi-label) | Strong primary target; use exploded labels. |
| `vehicle_type` | Predict from location, time, device; or correct misclassifications vs `updated_vehicle_type`. |
| `validation_status` (approved vs rejected) | Usable on validated subset; exclude `created1`/`processing`/`duplicate` or treat as separate class. |
| `police_station` / `center_code` | Predict jurisdiction from coordinates (geofencing inverse problem). |
| `data_sent_to_scita` | Binary outcome with clear class imbalance. |
| Violation count per grid cell / junction / hour | Aggregation target for forecasting. |
| `offence_code` | Redundant with `violation_type`; pick one to avoid label leakage. |

### 8.3 Targets That CANNOT (or Should NOT) Be Predicted

| Target | Reason |
|--------|--------|
| `closed_datetime` | 100% null — no labels exist. |
| `action_taken_timestamp` | 100% null — no labels exist. |
| `description` | 100% null — no text to predict. |
| **Exact future violation at specific lat/lon** | Individual event prediction at point level is unstable; aggregate forecasting is more realistic. |
| **Real-world fine amount / penalty** | Not present in dataset. |
| **Driver identity / owner details** | Not present (by design — anonymized). |
| **Updated vehicle number** | Post-hoc human correction; predicting it from initial capture is a validation-pipeline task, not operational prediction. |
| **Causal “will this vehicle re-offend tomorrow”** | Requires longer longitudinal window and external covariates; 5-month anonymized snapshot is insufficient for robust causal claims. |
| **`modified_datetime` / `validation_timestamp`** | These are process outcomes, not ground-truth violation attributes — predicting them has limited operational value. |

---

## 9. Feature Engineering Opportunities

### Temporal
- Extract hour, day-of-week, month, is_weekend, is_holiday (Karnataka calendar)
- Resolve timezone ambiguity; create `hour_local` and `hour_utc` variants
- Time since last violation at same location / by same device
- Rolling 7-day / 30-day violation counts per grid cell
- Cyclical encoding (sin/cos) for hour and day-of-week

### Geospatial
- H3 / geohash grid cells at resolutions 7–9
- Distance to nearest named junction (for `No Junction` rows)
- Distance to city center, major markets, metro stations
- Cluster coordinates (DBSCAN/KMeans) → `location_cluster_id`
- Parse `location` for pin code, neighborhood, road name (NLP/regex)
- Point-in-polygon: assign BBMP zone, ward, traffic police division
- Kernel density estimate surfaces for hotspot modeling

### Categorical encoding
- One-hot / target encoding for `vehicle_type`, `police_station`, `device_id`
- Multi-label binarization for `violation_type` (27 binary columns)
- Frequency encoding for high-cardinality IDs (`device_id`, `created_by_id`)
- Embedding layers for `device_id`, `junction_name` in deep models

### Multi-label / text parsing
- Parse `violation_type` and `offence_code` JSON strings into structured lists
- `violation_count` = number of simultaneous offences
- Binary flags: `has_wrong_parking`, `has_no_parking`, etc.
- Co-occurrence features for common violation pairs

### Validation pipeline
- Binary `was_validated`; `validation_outcome` collapsed to approved/rejected/other
- `vehicle_type_corrected` = (`vehicle_type` != `updated_vehicle_type`)
- `time_to_validation_hours`
- Officer/device approval rate historical features (careful: target leakage if predicting validation)

### Aggregation features (group-by)
- Violations per `device_id`, `created_by_id`, `police_station` (7-day rolling)
- Vehicle historical violation count (by anonymized plate)
- Junction violation rate vs station average (relative risk)
- Station × vehicle_type cross rates

### Data cleaning transforms
- Filter or flag 168 out-of-bbox coordinates
- Standardize `validation_status` (`created1` → investigate mapping)
- Drop or impute 5 rows with missing station/junction
- Handle April partial month in train/test splits (use time-based split)

---

## 10. Recommended Next Steps (Analysis → Build)

1. **Clarify timestamp timezone** with data owner before temporal modeling.
2. **Parse multi-label fields** into normalized tables (`violations`, `violation_labels`).
3. **Create spatial grid** (H3 res-8 recommended for Bengaluru street scale).
4. **Define primary hackathon objective** — recommended: *hotspot forecasting* or *violation type classification* ( strongest signal, clearest impact).
5. **Time-based train/test split** — e.g. train on Nov–Feb, validate on Mar, test on Apr (acknowledging Apr is partial).
6. **Exclude null columns** from pipeline: `description`, `closed_datetime`, `action_taken_timestamp`.

---

## 11. Appendix: Validation & SCITA Pipeline Snapshot

| Metric | Value |
|--------|-------|
| Records with validation data | 173,196 (58.0%) |
| Approved | 115,400 (38.7% of all) |
| Rejected | 49,754 (16.7% of all) |
| Unvalidated (null status) | 125,254 (42.0%) |
| `created1` | 7,044 |
| `processing` | 678 |
| `duplicate` | 320 |
| SCITA sent = True | 255,893 (85.7%) |
| SCITA sent = False | 42,557 (14.3%) |

---

*End of report. No dashboard, model, or pipeline was built per scope constraints.*
