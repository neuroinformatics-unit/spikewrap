(supported-formats)=
# Supported Formats

To manage project analysis, spikewrap must make some assumptions
on how the data is organised. 

Currently, only data from 
[Neuropixels](https://www.neuropixels.org/) probes acquired in 
[SpikeGLX](https://billkarsh.github.io/SpikeGLX/) or 
[OpenEphys](https://open-ephys.org/) are supported.

:::{admonition} Contact Us
:class: note

If you would like to see more formats supported, please don't hesitate to [get in contact](community).

:::

## Key data organisation levels

We briefly define the three folder levels that ``spikewrap`` expects to find:

subject:
: The experimental subject from which the data is recorded.

session:
: The experimental session in which the data was collected.

run:
: Multiple runs within an experimental session are supported. \
Runs are inferred based on the acquisition software (see [below](format-specific)).

## Supported data organisation schemes

[NeuroBlueprint](https://neuroblueprint.neuroinformatics.dev/latest/index.html)
is the recommended way to organise the project folder for spikewrap.

Briefly, a 
[NeuroBlueprint](https://neuroblueprint.neuroinformatics.dev/latest/index.html)
project is organised like:

```
└── rawdata/
    └── sub-001_.../
        └── ses-001_.../
            └── ephys  /
                └── <spikeglx or openephys output>
```
See the full 
[NeuroBlueprint specification](https://neuroblueprint.neuroinformatics.dev/latest/specification.html) 
for details. 

Otherwise, it is expected that the folder format of the data will have the levels:

`subject -> session -> recording`

For example:

```
└── my_subject_name/
    └── my_session_name/
        └── <spikeglx or openephys output>
```

:::{admonition} NeuroBlueprint
:class: note
(neuroblueprint-recommended)=
Upcoming features in ``spikewrap`` will make accessing data structures in 
[NeuroBlueprint](https://neuroblueprint.neuroinformatics.dev/latest/index.html)
format very convenient. This functionality will not be available for other organisation schemes.

All examples below are in 
[NeuroBlueprint](https://neuroblueprint.neuroinformatics.dev/latest/index.html)
format.
:::

(format-specific)=

## Acquisition-software specific organisation

We are keen to extend support to more [SpikeGLX](https://billkarsh.github.io/SpikeGLX/) 
and [OpenEphys](https://open-ephys.org/) use cases. Please 
[get in contact](community) with unsupported datasets.

::::{tab-set}
:::{tab-item} SpikeGLX


[SpikeGLX](https://billkarsh.github.io/SpikeGLX/) 
recordings (in this example output to `ses-001/ephys`) are typically formatted like:

```
└── ses-001/
    └── ephys/
        └── run-name_g0_imec0/
            ├── run-name_g0_t0.imec0.ap.bin
            └── run-name_g0_t0.imec0.ap.meta
```

Experiments that do no use multiple gates, triggers or `imec`
probes are immediately supported.

An experimental folder with [SpikeGLX](https://billkarsh.github.io/SpikeGLX/)-acquired
data might look like:

```
└── rawdata/
    └── sub-001  /
        └── ses-001/
            └── ephys/
                ├── run-001_g0_imec0/
                │   ├── run-001_g0_t0.imec0.ap.bin
                │   └── run-001_g0_t0.imec0.ap.meta
                └── run-002_g0_imec0/
                    ├── run-002_g0_t0.imec0.ap.bin
                    └── run-002_g0_t0.imec0.ap.meta
        
```

:::{dropdown} Recordings with multiple gates, trigers or `imec` probes

``spikewrap`` assumes that all folders within the session level
are separate runs. Multi-gate recordings will be treated
as separate runs. 

Therefore, you can distinguish runs either with the `run-name`, or 
keep the same `run-name` and acquire separate gates. However, if multiple
run names and multiple gates are mixed, all will be treated as separate runs.

Currently multiple `imec` probes are not supported.

For each run, only one recording is expected. Therefore, multi-trigger
recordings are not supported. 

Note runs are simply concatenated in ``spikewrap`` / [SpikeInterface](https://spikeinterface.readthedocs.io/en/stable/)
by **direct concatenation** of the data.
Use [catGT](https://billkarsh.github.io/SpikeGLX/help/dmx_vs_gbl/dmx_vs_gbl) for proper concatenation of multi-gate and trigger recordings.

:::

:::{tab-item} OpenEphys

Currently, the [flat binary format](https://open-ephys.github.io/gui-docs/User-Manual/Recording-data/Binary-format.html)
(the OpenEphys default) is supported.

[OpenEphys](https://open-ephys.org/) flat binary recordings
(in this example output to `ses-001/ephys`)
are organised like: 

```
└── ses-001/
    └── ephys/
        └── Recording Node 304/
            └── experiment1/
                ├── recording1
                └── recording2
                └── recording3
```

At this level, [OpenEphys](https://open-ephys.org/) has three concepts (`Recording Node`, `experiment` and `recording`)
but spikewrap expects only a single a set of runs.

Therefore, spikewrap will treat the `recording` folders as separate runs. 
This means that datasets with multiple `Recording Node` and `experiment` folders are not currently supported.

In the above, example, the `ses-001` will be associated with three runs (`recording1`, `recording2` and `recording3`).

:::

::::
