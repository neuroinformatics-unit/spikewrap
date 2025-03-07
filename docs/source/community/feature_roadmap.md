(roadmap)=
# Feature Roadmap

:::{attention}

Currently, the interface of ``spikewrap`` is under review. The features described
below will be added with high priority once the review is complete.

::::

## More Preprocessing Steps

Currently only ```phase_shift```, ```bandpass_filter``` and ```common_reference``` are exposed.
```

## Subject level

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

- logging
- store session / run information for data provenance

## Data Quality Metrics

- For all runs, write IBL's raw data quality metrics with images to output folder


## Postprocessing

- Many possibilities here ... etc. (spikeinterface sorting_analyzer, Phy, 'qualitymetrics', bombcell, unitmatch...)
