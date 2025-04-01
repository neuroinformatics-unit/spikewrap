# Feature Roadmap

> **Note:** The spikewrap interface is currently under review. The features listed below are planned for upcoming releases and may be implemented in no particular order.

## New and Extended Preprocessing Steps

### Raw Data Quality Metrics
- **Port IBL's raw data quality metrics:**  
  Integrate and port the IBL raw data quality metrics into SpikeInterface.
- **Output Diagnostic Images:**  
  Automatically generate and save diagnostic plots that detail raw data quality.

### Diagnostic Plots on Preprocessing
- **Output Diagnostic Plots:**  
  When running `save_preprocessed()`, automatically output plots (e.g., 500ms segments before and after each processing step) to disk for visual inspection.
- **Per-Step Visualization:**  
  Save images for each individual preprocessing step (e.g., raw, phase_shift, bandpass_filter, common_reference) to aid in troubleshooting and quality assessment.

### Conversion to NWB
- **NWB Export:**  
  Add functionality to convert preprocessed recordings to NWB (Neurodata Without Borders) format.
- **Integration with Pynapple:**  
  Optionally, link NWB conversion with pynapple for further downstream analysis.

### Extended Sync Channel Support
- **Enhanced Sync Integration:**  
  Expand support for sync channels (primarily via SpikeInterface improvements), with better integration into NWB conversion workflows.

### Exposing Motion Correction
- **Motion Correction Preprocessing:**  
  Integrate motion correction methods from SpikeInterface and expose them via spikewrap, making it easier to apply this step to your recordings.

### Wrapping CatGT
- **CatGT Integration:**  
  Develop a wrapper for CatGT, enabling its functionality to be integrated into the spikewrap pipeline.


## Existing and Future Enhancements

### More Preprocessing Steps
- **Current Steps:**  
  Currently, spikewrap exposes `phase_shift`, `bandpass_filter`, and `common_reference`.
- **Planned Additions:**  
  In future releases, additional preprocessing methods (as listed above) will be made available.

### Subject-Level Control
- **Multi-Session and Multi-Run Support:**  
  Extend the `Subject` class to allow processing and concatenation of multiple sessions and runs in one go.

  **Example:**
  ```python
  subject = sw.Subject(
     subject_path="...",
     sessions_and_runs={
          "ses-001": "all", 
          "ses-002": ["run-001", "run-003"],  # Exclude bad runs as needed
     },
  )

  subject.preprocess(
      "neuropixels+kilosort2_5", 
      per_shank=True, 
      concat_sessions=False, 
      concat_runs=True
  )

  subject.plot_preprocessed("ses-001", runs="all")


## Quality of Life

**Enhanced Logging:**
Improve logging and user feedback during processing.

**Data Provenance:**
Automatically store session/run information to aid in reproducibility and data provenance.

## Data Quality Metrics

- For all runs, write IBL's raw data quality metrics with images to output folder


## Postprocessing

**Integration with Sorting Analyzers and QC Tools:**
Incorporate tools such as SpikeInterface’s sorting_analyzer, Phy, and other quality metrics tools (e.g., bombcell, unitmatch) to facilitate robust postprocessing and quality assessment.