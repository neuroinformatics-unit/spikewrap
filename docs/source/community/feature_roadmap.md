(roadmap)=
# Feature Roadmap

:::{attention}

Currently, the interface of ``spikewrap`` is under review. The features described
below will be added with high priority once the review is complete.

::::

## Raw Data Quality Metrics

Generate and export IBL's raw data quality metrics with diagnostic images to the output folder for each run.

## Diagnostic Plots

Automatically output diagnostic plots to disk when running `save_preprocessed` to facilitate quality control without manual intervention.

## NWB Export

Support for converting preprocessed data and sorting results to Neurodata Without Borders (NWB) format for improved interoperability with other neuroscience tools.

## Extended Sync Channel Support

Improve handling of sync channels with better integration with SpikeInterface, linking with NWB conversion and pynapple.

## CatGT Integration

Wrap the CatGT tool for proper concatenation of multi-gate and trigger recordings in SpikeGLX data.

## Motion Correction

Expose motion correction capabilities for drift correction in long recordings.

## More Preprocessing Steps

Additional preprocessing steps will be exposed beyond the current ```phase_shift```, ```bandpass_filter```, ```common_reference```, and bad channel detection.

## Subject Level

Extending the level of control to ``Subject``, allowing the running and
concatenation of multiple sessions and runs at once.

```python
subject = sw.Subject(
   subject_path="...",
   sessions_and_runs={
        "ses-001": "all", 
        "ses-002": ["run-001", "run-003"], ...},  # e.g. sub-002 run-002 is bad
)

subject.preprocess(
    "neuropixels+kilosort2_5", 
    per_shank=True, 
    concat_sessions=False, 
    concat_runs=True
)

subject.plot_preprocessed("ses-001", runs="all")
```

## Quality of Life

- Enhanced logging for better tracking of processing steps
- Store session/run information for improved data provenance
