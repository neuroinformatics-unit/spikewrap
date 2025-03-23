# Output Folder Structure

:::{attention}
This output format is not set in stone. Please get in contact 
with any preferences on how you would like to see this organised.
:::

Here are two example output folders, depending on whether sessions
runs were concatenated and processing was performed per-shank.

Below are shown in 
[NeuroBlueprint style](https://neuroblueprint.neuroinformatics.dev/latest/specification.html), 
with outputs placed  in the root folder as ``rawdata``, in a folder called ``derivatives``. 

However, the output folder can  be overridden by passing the ``output_path`` argument to 
{class}`spikewrap.Session`.

## Runs concatenated, split by shank

```
└── derivatives/
    └── sub-001/
        └── ses-001/
            └── ephys/
                ├── run-001_g0_imec0/
                │   └── sync/
                │       └── sync_channel.npy
                ├── run_002_g0_imec0/
                │   └── sync/
                │       └── sync_channel.npy
                └── concat_run/
                    ├── preprocessed/
                    │   ├── shank_0/
                    │   │   └── si_recording/
                    │   │       └── <spikeinterface binary>
                    │   └── shank_1/
                    │       └── ...
                    ├── sorting/
                    │   └── ...
                    └── orig_run_names.txt
```

Here, the concatenated runs are stored in a folder with the canonical name
``concat_run``. The names of the original runs and their concatenation order
are stored in ``orig_run_names.txt``. Note that sync runs are always saved
per-run and are not concatenated, to avoid [incorrect assumptions](https://github.com/billkarsh/CatGT/blob/1ad1abe894e07d5fa3cb0439961d162caba34628/Build/ReadMe.md?plain=1#L1121).

## No run concatenation, not split by shank

```
└── derivatives/
    └── sub-001/
        └── ses-001/
            └── ephys/
                ├── run-001_g0_imec0/
                │   ├── preprocessed/
                │   │   └── si_recording/
                │   │       └── <spikeinterface binary>
                │   ├── sync/
                │   │   └── sync_channel.npy
                │   └── sorting/
                │       └── ...
                └── run-001_g0_imec0/
                    └── ...  
```
