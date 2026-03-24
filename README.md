# Repository for “Quantifying Cyber-Vulnerability in Power Electronic Systems via an Impedance-Based Attack Reachable Domain”

This repository provides supplementary models, scripts, datasets, and result files associated with the paper:

**“Quantifying Cyber-Vulnerability in Power Electronic Systems via an Impedance-Based Attack Reachable Domain”**

## Overview

This repository is organized as a compact supplementary package for the paper.

It includes:

- representative materials for the practical gray-box route discussed in the paper;
- reported benchmark result files for the 4-bus and 39-bus case studies.

## Structure

```text
.
├─ README.md
├─ 4bus/
│  ├─ 4busREADME.md
│  ├─ era_example/
│  ├─ Surrogate_example/
│  └─ results/
└─ 39bus/
   ├─ 39busREADME.md
   ├─ system_parameters.md
   ├─ bus_strength_api.csv
   └─ 39BusScope.png
```

## 4-Bus Package

The `4bus/` folder serves two purposes:

- to illustrate the practical gray-box route used in the paper;
- to provide the reported 4-bus result files.

In particular:

- `era_example/` shows a representative disturbance-based impedance-identification example;
- `Surrogate_example/` shows a representative surrogate-model example for IBR1;
- `results/` stores the reported 4-bus ARD and time-domain validation figures.

See `4bus/4busREADME.md` for a compact description of the workflow.

## 39-Bus Package

The `39bus/` folder focuses on the reported 39-bus study.

It contains:

- `39busREADME.md` for a brief description of the 39-bus package;
- `system_parameters.md` for the main synchronous-generator and GFM-IBR parameter summary;
- `bus_strength_api.csv` for the reported bus-level MISCR, IMR, and API results;
- `39BusScope.png` for the representative time-domain validation figure.

## Scope

This repository is intended to provide:

- representative workflow materials for the practical gray-box setting;
- benchmark-system result files corresponding to the reported studies;
- supplementary code/data that help readers understand the reported pipeline.

It is not intended to include every intermediate development asset used during the research process.

## Citation

If you use this repository in your research, please cite:

```bibtex
@article{zhen2026ard,
  title   = {Quantifying Cyber-Vulnerability in Power Electronic Systems via an Impedance-Based Attack Reachable Domain},
  author  = {Zhen, Hongwei and Yu, Ze and Xiang, Xin and Li, Wuhua and He, Xiangning and Sun, Mingyang},
  journal = {IEEE Transactions on Power Electronics},
  note    = {submitted}
}
```

## Contact

For questions regarding this repository, please contact the authors through the corresponding paper information.
