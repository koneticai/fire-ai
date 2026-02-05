# Fire Doors Rules Extraction Report

**Generated:** 2026-02-04
**Standard:** AS 1851-2012 (Amendment 1, November 2016)
**Rules Extracted:** FD-01 to FD-20

---

## 1. EXECUTIVE SUMMARY

| Metric | Value |
|--------|-------|
| Total Rules Extracted | 20 |
| Baseline Rules | 3 |
| Six-Monthly Rules | 11 |
| Annual Rules | 6 |
| Average Confidence | 0.93 |

### Section 12 Coverage
- **12.4.3.1** Hinged/Pivoted Fire Doors: Covered
- **12.4.3.2** Horizontal Sliding Fire Doors: Gap identified
- **12.4.4** Smoke Doors: Gap identified
- **12.4.5** Fire Shutters: Out of scope (separate system)

---

## 2. BASELINE RULES (FD-01 to FD-03)

### FD-01: Fire Door Identity & Baseline Data
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-01 | 1.00 |
| Frequency | Baseline (onboarding) | 1.00 |
| AS1851 Reference | Table 12.4.3.1 Item 1.1 | 1.00 |

**Required Data:**
- Building/door location
- Fire Resistance Level (FRL)
- Proprietary door type
- Approved design reference
- Commissioning certification

### FD-02: Hardware Specification (Baseline)
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-02 | 0.95 |
| Frequency | Baseline (onboarding) | 1.00 |
| AS1851 Reference | Table 12.4.3.1 Items 1.5-1.11 | 0.95 |

**Required Hardware Verification:**
- Hinge type/model (fire-tested)
- Door closer type/model (fire-tested)
- Latch/lock mechanism
- Seal specification (intumescent/smoke)
- Vision panel glazing (if applicable)

### FD-03: Commissioning Certification
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-03 | 0.95 |
| Frequency | Baseline (onboarding) | 1.00 |
| AS1851 Reference | Section 12.2 | 0.95 |

**Required Documentation:**
- Commissioning report
- As-built test results
- Installation compliance verification
- Competent person sign-off

---

## 3. SIX-MONTHLY RULES (FD-04 to FD-14)

### FD-04: Visual Damage Inspection
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-04 | 0.95 |
| Frequency | Six-monthly | 1.00 |
| AS1851 Reference | Table 12.4.3.1 Item 1.12 | 0.95 |

**Inspection Points:**
- Door leaf damage (delamination, warping, bowing)
- Frame distortion
- Edge condition (splitting, damage)
- Threshold integrity

**Classification Logic:**
```json
{
  "PASS": "No visible damage affecting fire integrity",
  "FAIL": "Any damage compromising FRL or operation"
}
```

### FD-05: Self-Closing Mechanism Test
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-05 | 1.00 |
| Frequency | Six-monthly | 1.00 |
| AS1851 Reference | Table 12.4.3.1 Item 1.8 | 1.00 |

**Test Procedure:**
1. Open door to 70° position
2. Release and verify full closure
3. Open door to 15° position
4. Release and verify full closure with latch engagement

**Classification Logic:**
```json
{
  "PASS": {
    "conditions": [
      "closes_from_70_degrees == true",
      "closes_from_15_degrees == true",
      "latches_when_closed == true"
    ]
  }
}
```

### FD-06: Latch Engagement Test
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-06 | 1.00 |
| Frequency | Six-monthly | 1.00 |
| AS1851 Reference | Table 12.4.3.1 Item 1.9 | 1.00 |

**Pass Criteria:**
- Latch engages positively when door closes
- Bolt extends fully into strike plate
- No binding or sticking

### FD-07: Door Seals Condition
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-07 | 0.95 |
| Frequency | Six-monthly | 1.00 |
| AS1851 Reference | Table 12.4.3.1 Item 1.7 | 0.95 |

**Inspection Points:**
- Intumescent seals present and undamaged
- Smoke seals continuous around perimeter
- Bottom seal contact adequate
- No gaps in seal coverage

### FD-08: Closer Operation & Condition
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-08 | 0.95 |
| Frequency | Six-monthly | 1.00 |
| AS1851 Reference | Table 12.4.3.1 Item 1.10 | 0.95 |

**Inspection Points:**
- Closer body/arm free from obstruction
- Full swing operation without binding
- No oil/fluid leakage
- Mounting brackets secure

### FD-09: Hinge Condition & Alignment
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-09 | 0.95 |
| Frequency | Six-monthly | 1.00 |
| AS1851 Reference | Table 12.4.3.1 Item 1.11 | 0.95 |

**Inspection Points:**
- Hinges wear-free
- Aligned correctly
- Smooth operation
- Securely fastened to leaf and frame

### FD-10: Gap & Clearance Measurements
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-10 | 1.00 |
| Frequency | Six-monthly | 1.00 |
| AS1851 Reference | Table 12.4.3.1 Item 1.4 | 1.00 |

**Critical Thresholds (per AS 1905.1):**
- Perimeter gaps: Typically ≤3mm with seals
- Bottom gap: As specified by manufacturer
- Meeting stile gaps (pairs): Per proprietary design

**Classification Logic:**
```json
{
  "PASS": {
    "conditions": [
      "perimeter_gap_mm <= max_allowed",
      "bottom_gap_mm <= manufacturer_spec",
      "seals_provide_continuous_contact == true"
    ]
  }
}
```

### FD-11: Hardware Security Verification
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-11 | 0.90 |
| Frequency | Six-monthly | 1.00 |
| AS1851 Reference | Table 12.4.3.1 Item 1.6 | 0.90 |

**Verification Points:**
- All hardware securely attached
- Correct fittings per AS 1905.1
- No non-approved attachments added
- Kick plates secure (if fitted)

### FD-12: Marking & Signage Compliance
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-12 | 0.90 |
| Frequency | Six-monthly | 1.00 |
| AS1851 Reference | Table 12.4.3.1 Item 1.3 | 0.90 |

**Required Markings:**
- Door leaf/frame tags per AS 1905.1
- Statutory signage ("Fire Door - Keep Closed")
- FRL identification
- Manufacturer identification

### FD-13: Fire Rating Verification
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-13 | 0.95 |
| Frequency | Six-monthly | 1.00 |
| AS1851 Reference | Table 12.4.3.1 Item 1.2 | 0.95 |

**Verification:**
- FRL matches approved design
- Door frame stop dimensions per proprietary type
- No modifications affecting FRL

### FD-14: Frame Integrity & Anchorage
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-14 | 0.90 |
| Frequency | Six-monthly | 1.00 |
| AS1851 Reference | Table 12.4.3.1 Items 1.13-1.14 | 0.90 |

**Inspection Points:**
- Frame free from excessive distortion
- Adequately anchored to walling
- Striker plate present and functional
- Steel frame back-fill verified (if applicable)

---

## 4. ANNUAL RULES (FD-15 to FD-20)

### FD-15: Annual Door Opening Force Test
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-15 | 1.00 |
| Frequency | Annual | 1.00 |
| AS1851 Reference | Table 12.4.3.1 Item 1.5a | 1.00 |

**Critical Threshold:**
- **Maximum 110 N** door opening force under worst-case pressurization

**Test Procedure:**
1. Simulate fire mode pressurization (if applicable)
2. Measure force required to open door
3. Record at handle height

**Classification Logic:**
```json
{
  "PASS": "opening_force_N <= 110",
  "FAIL": "opening_force_N > 110"
}
```

### FD-16: Paint & Coating Integrity
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-16 | 0.85 |
| Frequency | Annual | 0.95 |
| AS1851 Reference | Table 12.4.3.1 Item 1.12 | 0.85 |

**Inspection Points:**
- Intumescent paint/coating intact
- No flaking or damage exposing substrate
- Touch-up applied where required

### FD-17: Vision Panel Inspection
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-17 | 0.90 |
| Frequency | Annual | 1.00 |
| AS1851 Reference | Table 12.4.3.1 Item 1.15 | 0.90 |

**Inspection Points:**
- Glazing approved for door type
- Glass sound and crack-free
- Perimeter trim secure
- All fixings in place
- Fire-rated glazing identification visible

### FD-18: Full Operation Test
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-18 | 0.90 |
| Frequency | Annual | 1.00 |
| AS1851 Reference | Section 12.3 | 0.90 |

**Test Procedure:**
- Complete open/close cycle under simulated load
- Verify smooth operation without binding
- Confirm self-closing from multiple angles
- Latch engagement verification

### FD-19: Annual Condition Report
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-19 | 0.85 |
| Frequency | Annual | 1.00 |
| AS1851 Reference | Section 12.3 | 0.85 |

**Report Contents:**
- Summary of all tests performed
- Comparison to baseline condition
- Defect log with status
- Recommendations for remediation
- Compliance statement

### FD-20: Defect Event Management
| Attribute | Value | Confidence |
|-----------|-------|------------|
| Rule Code | AS1851-2012-FD-20 | 0.90 |
| Frequency | Ad-hoc | 1.00 |
| AS1851 Reference | Section 2.4 | 0.90 |

**Defect Management:**
- Damage/non-compliance identification
- Risk assessment (critical vs non-critical)
- 24-hour notification for critical defects
- Remediation tracking
- Post-repair verification

---

## 5. RULE SCHEMA STRUCTURE

### Example: FD-05 Self-Closing Test Schema
```json
{
  "rule_code": "AS1851-2012-FD-05",
  "rule_name": "Fire Door - Six-Monthly Self-Closing Test",
  "test_frequency": "six_monthly",
  "applicable_standard": "AS1851-2012",
  "section_reference": "Table 12.4.3.1 Item 1.8",
  "rule_schema": {
    "test_inputs": {
      "door_id": {"type": "string", "required": true},
      "test_date": {"type": "date", "required": true},
      "tester_name": {"type": "string", "required": true}
    },
    "test_results": {
      "closes_from_70_degrees": {"type": "boolean", "required": true},
      "closes_from_15_degrees": {"type": "boolean", "required": true},
      "latches_when_closed": {"type": "boolean", "required": true},
      "closing_time_seconds": {"type": "number", "min": 0, "max": 30}
    },
    "classification_logic": {
      "PASS": {
        "conditions": [
          "closes_from_70_degrees == true",
          "closes_from_15_degrees == true",
          "latches_when_closed == true"
        ]
      },
      "FAIL": {
        "conditions": [
          "closes_from_70_degrees == false",
          "closes_from_15_degrees == false",
          "latches_when_closed == false"
        ]
      }
    }
  }
}
```

---

## 6. COVERAGE GAP ANALYSIS

### Identified Gaps in FD-01 to FD-20

| Gap Category | Items Missing | Priority |
|--------------|---------------|----------|
| Horizontal Sliding Fire Doors | 24 items | HIGH |
| Smoke Doors | 26 items | HIGH |
| Fire Shutters | Out of scope | N/A |
| Hold-open device tests | 1 item | MEDIUM |
| Pair door meeting stiles | 2 items | MEDIUM |

### Recommendation
Expand fire door rule set to include:
- **FD-SLIDE-xx:** Sliding fire door rules (three-monthly + six-monthly)
- **FD-SMOKE-xx:** Smoke door rules (six-monthly)

See COVERAGE-GAP-ANALYSIS.md for detailed requirements.

---

## 7. RESIDENTIAL APARTMENT EXCEPTION

**AS1851-2012 Section 12.4.3.1 Note 1:**

> "Hinged and pivoted fire-resistant doorsets serving as entry doors to private residential apartments may be extended to a yearly service schedule."

**Impact:** FD-04 through FD-14 (six-monthly) may be extended to yearly for residential apartment entry doors. Baseline rules (FD-01 to FD-03) still apply at onboarding.

---

## 8. CONFIDENCE SUMMARY

| Rule Range | Average Confidence | Status |
|------------|-------------------|--------|
| FD-01 to FD-03 | 0.97 | Baseline extracted |
| FD-04 to FD-14 | 0.93 | Six-monthly extracted |
| FD-15 to FD-20 | 0.88 | Annual extracted |
| **OVERALL** | **0.93** | **20 rules extracted** |

---

*Report generated by Fire AI M3 Research Swarm*
*Agents: ac1e201, a9a242d, a4989db*
