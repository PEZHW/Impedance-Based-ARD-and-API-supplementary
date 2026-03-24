# 39-Bus Package

This folder contains the supplementary materials for the reported 39-bus case study in the paper:

**“Quantifying Cyber-Vulnerability in Power Electronic Systems via an Impedance-Based Attack Reachable Domain”**

## Overview

This package focuses on the reported **system-level vulnerability ranking** results for the modified IEEE 39-bus system.

In this test case, nine generators other than Bus 39 are replaced by inverter-based resources (IBRs). The resulting system remains nominally stable with a gSCR of 4.845, while the proposed API reveals bus-level cyber-vulnerability patterns that cannot be inferred from nominal-strength indicators alone.

## Files

- `README.md`  
  Brief description of the 39-bus package.

- `system_parameters.md`  
  Summary of the main synchronous-generator and GFM-IBR parameters used in the reported 39-bus study.

- `bus_strength_api.csv`  
  Bus-level MISCR, IMR, and API values corresponding to Table II in the paper.

- `39BusScope.png`  
  Representative time-domain validation result corresponding to Fig. 5 in the paper.

## Notes

This package is organized as a compact **results-oriented supplementary package**.

It includes:
- key system parameter summaries,
- reported bus-level vulnerability metrics,
- representative time-domain validation results.

It is not intended to include the complete Simulink development model or every intermediate simulation asset used during the research process.

## Key Result

The reported 39-bus results show that API is not monotonic with either MISCR or IMR. Bus 37 has the largest API, followed by Buses 34 and 36, while Bus 32 is only weakly attack-reachable.  In particular, the pronounced vulnerability of Bus 36, overlooked by nominal-strength indicators, is correctly captured by the proposed API. The time-domain validation further shows that attacks on higher-API buses induce more severe system-level disturbances.

## Relation to the Paper

This package corresponds to the 39-bus case study reported in the manuscript, including:
- bus-level vulnerability ranking across the IBR buses,
- comparison with nominal-strength indicators,
- representative validation under worst-case joint attacks.

The time-domain comparison in `39BusScope.png` corresponds to the validation cases where the worst-case joint manipulation targets Bus 37, Bus 32, and Bus 36, respectively.