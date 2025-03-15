# spikewrap

``spikewrap`` is a tool for automating extracellular electrophysiology analysis.

See the documentation for a quick
[feature overview](https://spikewrap.neuroinformatics.dev/gallery_builds/get_started/feature_overview.html)
and to [get started](https://spikewrap.neuroinformatics.dev/get_started/index.html).

## Overview

``spikewrap`` provides a lightweight interface to manage the preprocessing and sorting 
of extracellular electrophysiological data. 

Built on [SpikeInterface](https://spikeinterface.readthedocs.io/en/stable/api.html), ``spikewrap`` offers a convenient wrapper
to run sorting pipelines. It aims to facilitate the sharing of electrophysiology pipelines and standardize project folders.

For example, all runs for a recording session can be preprocessed with:

```python
import spikewrap as sw

subject_path = sw.get_example_data_path() / "rawdata" / "sub-001"

session = sw.Session(
    subject_path=subject_path,
    session_name="ses-001",
    file_format="spikeglx",  # or "openephys"
    run_names="all",
    probe=None,  # optional argument to set probe (neuropixels auto-detected)
)

session.save_sync_channel()

session.preprocess(
    configs="neuropixels+kilosort2_5",
    per_shank=True,
    concat_runs=False,
)

session.save_preprocessed(
    overwrite=True,
    n_jobs=12,
    slurm=True
)
```

This will output a folder structure like:

```
└── derivatives/
    └── sub-001/
        └── ses-001/
            └── ephys/
                ├── run-001/
                │   ├── preprocessed/
                │   │   ├── shank_0/
                │   │   │   └── si_recording/
                │   │   │       └── <spikeinterface binary>
                │   │   └── shank_1/
                │   │       └── si_recording/
                │   │           └── <spikeinterface binary>      
                │   └── sync/
                │       └── sync_channel.npy
                └── run-002/
                    └── ...    
```                   

## Installation

``pip install spikewrap`` 

## Get Involved

Contributions to ``spikewrap`` are welcome and appreciated! Please see our [contributing guide](https://spikewrap.neuroinformatics.dev/community/contributing_guidelines.html) for details, and don't hesitate to ask any questions on our [Zulip Chat](https://neuroinformatics.zulipchat.com/#narrow/stream/406002-Spikewrap).
