# Supplementary Materials for  
**Quantifying Cyber-Vulnerability in Power Electronic Systems via an Impedance-Based Attack Reachable Domain**

This repository provides supplementary materials for the above IEEE TPEL Letter.  
It is intended as a lightweight companion repository to support the reported case studies, due to the space limitation of the Letter format.

The repository includes:

- Simulink models of the 4-bus benchmark system and the modified IEEE 39-bus system
- Detailed parameter files for system configuration, VSG-controlled IBRs, and attack settings
- Processed impedance-identification results used for surrogate construction
- Processed surrogate-model outputs and representative inference results
- Source data for the main figures and tables in the paper
- Selected plotting and post-processing scripts for reproducing the reported results

This repository is **not** a full release of the complete end-to-end workflow.  
In particular, large-scale simulation pipelines, full training code, and all intermediate files are not included unless explicitly noted.  
Instead, the goal is to provide the model files, key parameters, and processed results necessary to understand and verify the main claims of the paper.

## Repository Structure

- `models/`: Simulink models and initialization files
- `parameters/`: detailed parameter settings and representative attack cases
- `impedance_identification/`: processed impedance-identification data
- `surrogate_results/`: trained surrogate artifacts and example outputs
- `paper_results/`: source data corresponding to figures and tables in the paper
- `scripts/`: selected scripts for plotting and post-processing

## Relation to the Paper

This repository supports the results reported in:

- Fig. 3: ARDs of the two dominant modes in the 4-bus system
- Table I: API values of the 4-bus case
- Fig. 4: time-domain validation in the 4-bus system
- Table II: MISCR, IMR, and API values in the modified IEEE 39-bus system
- Fig. 5: time-domain validation of bus-level vulnerability ranking

For questions regarding unavailable intermediate materials, please refer to the manuscript for methodological details and to the processed results provided here.
