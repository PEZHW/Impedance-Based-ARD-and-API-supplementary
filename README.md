# Repository for “Quantifying Cyber-Vulnerability in Power Electronic Systems via an Impedance-Based Attack Reachable Domain”

This repository provides the supplementary models, codes, datasets, and result files associated with the paper:

**“Quantifying Cyber-Vulnerability in Power Electronic Systems via an Impedance-Based Attack Reachable Domain”**

## Overview

This repository supports the reproducibility of the workflow materials and benchmark-study results reported in the paper.

The paper develops an impedance-based Attack Reachable Domain (ARD) framework and the corresponding Attack Penetration Index (API) for attacker-oriented cyber-vulnerability assessment in power electronic systems. It also discusses a practical gray-box workflow based on impedance identification and differentiable surrogate tools.

To match the structure of the paper, this repository contains two benchmark-system packages:

- a **4-bus package**, including representative workflow materials and benchmark-study results;
- a **39-bus package**, including system-level ARD/API evaluation and representative attack-validation results.

## Repository Structure

```text
.
├─ README.md
├─ 4bus/
│  ├─ 4bus_model.slx
│  ├─ transient_data.mat
│  ├─ era and identified_impedance.m
│  ├─ source_dataset.csv
│  ├─ train_pinn.py
│  ├─ trained_model.pt
│  ├─ compute_ard_api.m
│  ├─ table1_results.csv
│  ├─ fig3_fig4_data.mat
│  └─ worst_case_validation.mat
├─ 39bus/
│  ├─ 39bus_model.slx
│  ├─ compute_ard_api.m
│  ├─ table2_results.csv
│  ├─ fig5_data.mat
│  └─ validation_cases.mat
└─ supplementary/
   ├─ workflow_note.md
   └─ data_dictionary.md
````

## 4-bus Package

The `4bus/` folder contains:

* the Simulink model of the 4-bus benchmark system;
* representative disturbance-generated transient data;
* ERA-based impedance-identification code and results;
* source dataset and PINN surrogate-training materials;
* ARD/API computation results for the reported 4-bus case;
* worst-case attack validation results corresponding to the reported study.

This package is intended to support the 4-bus case study in the paper, where the ARDs of two dominant modes are compared under operating-point manipulation, control-parameter tampering, and coordinated joint manipulation.

## 39-bus Package

The `39bus/` folder contains:

* the Simulink model of the modified IEEE 39-bus system;
* ARD/API evaluation results for the IBR buses;
* representative time-domain validation cases.

This package is intended to support the 39-bus case study in the paper, which demonstrates bus-level cyber-vulnerability ranking in a larger inverter-dominated system.

## Scope of This Repository

This repository is intended to provide:

* supplementary implementation materials for the proposed workflow;
* benchmark-system result files corresponding to the reported ARD/API studies;
* representative data and code for impedance identification and surrogate preparation.

It is not intended to include every intermediate development asset used during the research process.

## Notes

The repository includes both workflow-related materials and benchmark-study results.

For the 4-bus case, the repository contains representative materials for:

* disturbance generation,
* impedance identification,
* surrogate preparation,
* ARD/API evaluation,
* worst-case attack validation.

For the 39-bus case, the repository focuses on:

* benchmark-system ARD/API evaluation,
* bus-level vulnerability comparison,
* representative attack-validation results.

## Citation

If you use this repository in your research, please cite:

```bibtex
@article{zhen_ard_api_pes,
  title   = {Quantifying Cyber-Vulnerability in Power Electronic Systems via an Impedance-Based Attack Reachable Domain},
  author  = {Zhen, Hongwei and Yu, Ze and Xiang, Xin and Li, Wuhua and He, Xiangning and Sun, Mingyang},
  journal = {IEEE Transactions on Power Electronics},
  note    = {submitted}
}
```

## Contact

For questions regarding this repository, please contact the authors through the corresponding paper information.
