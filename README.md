# Cross-Channel Prediction, Classification, and Individual Retention in Low-Channel EEG Adaptation

Authors: Yiming Shen (University of Massachusetts Boston; corresponding author) and Xi Jiang (University of Chicago).

This repository provides the versioned archived-results package accompanying the manuscript. The package contains the current LaTeX source, saved result records, figure and numerical checks, frozen protocols, statistical-methods records, and available experiment implementations. The reproduction instructions distinguish the commands actually verified from archived code retained for inspection.

## Obtain and verify the package

Download the archive, checksum and validation report from [release v1.1.0](https://github.com/Yiming-S/low-channel-eeg-adaptation/releases/tag/v1.1.0). Extract the archive and read `paper/reproducibility/README.md`. Run the documented commands from the extracted package root. The figure build and numerical checks use archived records; a separate independent NumPy script recomputes the principal participant-bootstrap intervals from compact participant endpoints.

Version v1.1.0 includes the revised manuscript, the four-panel Lee main figure, participant-level distribution checks, and compact paired-trial inputs for the original Stieger reduced-label old-test comparison. The release verification independently reconstructs the added summaries and tables after extraction outside the research checkout. The original v1.0.0 archive is retained.

Raw EEG, encoder weights, feature caches and full fitted-model/prediction archives remain separate inputs to preprocessing and model fitting. Their acquisition and use follow the original dataset distributions and stage-specific protocols.

## Data sources

- Stieger et al., Scientific Data (2021): https://doi.org/10.1038/s41597-021-00883-1
- Lee et al., GigaScience (2019): https://doi.org/10.1093/gigascience/giz002
- Yang et al., Scientific Data (2025): https://doi.org/10.1038/s41597-025-04826-y
- Farabbi et al., Zenodo: https://doi.org/10.5281/zenodo.5882500

The manuscript and methods records retain each experiment's development, confirmation, and descriptive roles. The source inventory identifies external runtime inputs that are not supplied by this release.
