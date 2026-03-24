# 4-Bus Package

  This folder contains the 4-bus benchmark materials for the paper  
  **“Quantifying Cyber-Vulnerability in Power Electronic Systems via an Impedance-Based Attack Reachable Domain”**.

  It serves two purposes:

  - to illustrate the practical gray-box route used in the paper;
  - to provide the reported 4-bus result files.

## Structure

  ```text
  4bus/
  ├─ era_example/
  ├─ Surrogate_example/
  └─ results/
  ```

## Contents

  ### `era_example/`

  Representative example of disturbance-based impedance identification.

  This folder includes:

  - the 4-bus Simulink model,
  - transient voltage/current data,
  - ERA-based identification code,
  - a representative impedance-identification result.

  ### `Surrogate_example/`

  Representative example of surrogate preparation for the gray-box workflow.

  This folder includes:

  - the source dataset for IBR1,
  - surrogate training code,
  - a trained model checkpoint,
  - representative training and prediction results.

  Running the training script will generate terminal outputs and saved result figures.

  ### `results/`

  Reported 4-bus results corresponding to the paper.

  This folder stores:

  - the ARD figure for the 4-bus case,
  - the time-domain validation figure under worst-case attacks.

  ## Notes

  This package is organized to show the practical workflow in a compact form:

  **disturbance data → impedance identification → surrogate preparation → reported 4-bus results**

  It is intended as a minimal supplementary package rather than a complete development repository.