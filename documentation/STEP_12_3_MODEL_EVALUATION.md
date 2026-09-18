# STEP 12.3 — MODEL EVALUATION & SCIENTIFIC VALIDATION REPORT

## Overview
This document presents the scientific evaluation and validation findings for the SIH 2026 AI/ML Landslide Hazard & Risk Model across Kohima and Aizawl districts.

---

## 1. Validation Strategy & Partitioning
- **Validation Framework**: Spatial 5 km × 5 km Block Partitioning and Positive-Unlabeled (PU) Distance Evaluation.
- **Verified Positive Events**: 11 cells (`KOH_01378`, `KOH_03175`, `KOH_03071`, `KOH_01187`, `KOH_02654`, `AIZ_01960`, `AIZ_02185`, `AIZ_02321`, `AIZ_02559`, `AIZ_02314`, `AIZ_02431`).
- **Verified Negative Events**: 0 cells.
- **Unlabeled Cells**: 16950 cells.

---

## 2. Evaluation Metrics Summary

| Metric | Computed Value | Status |
| :--- | :--- | :--- |
| **Spatial Hit Rate** | **100.0%** (11/11 verified cells) | Validated against baseline TSI |
| **Precision** | `NOT_COMPUTABLE_INSUFFICIENT_VERIFIED_LABELS` | Insufficient negative labels |
| **Recall** | `NOT_COMPUTABLE_INSUFFICIENT_VERIFIED_LABELS` | Insufficient ground truth sample |
| **F1 Score** | `NOT_COMPUTABLE_INSUFFICIENT_VERIFIED_LABELS` | Insufficient ground truth sample |
| **ROC-AUC** | `NOT_COMPUTABLE_INSUFFICIENT_VERIFIED_LABELS` | Insufficient ground truth sample |
| **PR-AUC** | `NOT_COMPUTABLE_INSUFFICIENT_VERIFIED_LABELS` | Insufficient ground truth sample |
| **Brier Score** | `NOT_COMPUTABLE_INSUFFICIENT_VERIFIED_LABELS` | Dynamic sensor calibration pending |
| **False Alarm Rate** | `NOT_COMPUTABLE_INSUFFICIENT_VERIFIED_LABELS` | Insufficient ground truth sample |

---

## 3. Scientific Justification
Conventional binary classifier metrics require both verified positive ($y=1$) and verified negative ($y=0$) labels. Substituting unlabelled cells as false negatives produces biased, scientifically invalid accuracy figures. Per Phase 7 data integrity guidelines, uncomputable metrics return explicit `NOT_COMPUTABLE_INSUFFICIENT_VERIFIED_LABELS` status.
