# ruff: noqa: E402
"""
.. _sorting-tutorial:

Sorting
=======

.. note::
    This is a long-form tutorial on sorting. See :ref:`here <sorting-howto>` for a quick how-to.

"""

# %%
# Running Sorting after Preprocessing
# -----------------------------------
#
# Spike sorting can be run on preprocessed data, even without saving to disk,
# using the :class:`spikewrap.Session.sort` function:
# TODO: LINK https://spikeinterface.readthedocs.io/en/latest/modules/sorters.html#internal-sorters
# https://spikeinterface.readthedocs.io/en/latest/modules/sorters.html#external-sorters-the-wrapper-concept

import spikewrap as sw

session = sw.Session(
    subject_path=sw.get_example_data_path() / "rawdata" / "sub-001",
    session_name="ses-001",
    file_format="spikeglx",  # or "openephys"
    run_names="all"
)

session.preprocess(
    configs="neuropixels+mountainsort5", concat_runs=True
)

session.sort(
    "neuropixels+mountainsort5",
    run_sorter_method="local",
    per_shank=True,
    concat_runs=False,
)

# %%
# In this example, all runs found in the session folder will be
# preprocessed. Then, preprocessed runs will be concatenated
# before sorting.
#
# Sorting results are output to a `sorting` folder in the
# output run folder, for example
#
# .. code-block::
#    └── my_project/
#        └── derivatives/
#            └── sub-001  /
#                └── ses-001/
#                    └── ephys/
#                        ├── concat_run/
#                        │   ├── preprocessed/
#                        │   │   └── <preprocessed_data>
#                        │   ├── sync/
#                        │   │   └── <sync_data>
#                        │   └── sorting/
#                        │       └── shank_0
#                        │           └── ...
#                        │       └── shank_1
#                        │           └── ...
#                        └── ...
#
# The ``per_shank`` and ``concat_runs`` arguments indicate whether
# the recording should be split per shank or concatenated
# prior to sorting. If the recording has already been split-by-shank
# and / or concatenated before preprocessing, they will remain so for sorting.
#
# The ``run_sorter_method`` indicates the method used to run the sorter.
# For sorters written in python (e.g. kilosort4, mountainsort5), these
# can be installed in the current environment and ``"local"`` used.
# Otherwise, the path to a matlab repository can be used, or ``docker``
# or ``singularity`` used to run in a container. See
# :class:`spikewrap.Session.sort` for a full explaination of the accepted arguments.
#
#
# Running Sorting from Saved Preprocessing
# ----------------------------------------
#
# Alternatively, the preprocessed data might be saved:

session = sw.Session(
    subject_path=sw.get_example_data_path() / "rawdata" / "sub-001",
    session_name="ses-001",
    file_format="spikeglx",  # or "openephys"
    run_names="all"
)

# TODO: turn off mountainsort filter
session.preprocess(
    configs="neuropixels+mountainsort5", concat_runs=True
)

session.save_preprocessed(overwrite=True)

# %%
# In this case, sorting can be run immediately after preprocessing, as above.
# Otherwise, the preprocessing can be loaded at a later date for sorting:

session = sw.Session(
    subject_path=sw.get_example_data_path() / "rawdata" / "sub-001",
    session_name="ses-001",
    file_format="spikeglx",
    run_names=["concat_run"]
)

# Here, the preprocessed data will be detected and loaded from disk, if available.
# Otherwise, an error will be raised.

# run names to sort TODO CHECK THIS IS NOT A STR IF NOT ALL ALSO TODO YOU CAN HAVE MIXED PP RUNS WHEN LOADING FROM DISK!!
# TODO: why does this not raise if no save data done? TODO: review and add asserts

session.sort(
    configs="neuropixels+mountainsort5", run_sorter_method="local"
)

# %%
# .. note::
#
#    The sorting will always run on the most recent preprocessing. For example:
#
#    .. code-block::
#
#        session.preprocess(configs_dict_1)
#
#        session.save_preprocessed()
#
#        session.preprocess(configs_dict_2)
#
#        session.sort()
#
#    In this case, sorting will be run on the data preprocessed by ``configs_dict_2``.
#    As such, it is recommended to save the preprocessed data only when
#    configurations have been decided on.

# %%
# Ways to run the sorter
# ----------------------------------------
#
# The ``run_sorter_method`` argument specifies the method used to run the sorter.
# These are based on the extensive options provided by the SpikeInterface package,
# which provide great flexibility in ways that sorters can be run.
#
# ``"local"``:
#   Should be used if the sorter can be run in the current python environment,
#   (i.e. it is a sorter written in Python, such as ``"kilosort4"`` or ``"spykingcircus2"``.s
#
# A ``Path``:
#    If the sorter is written in Matlab (e.g. kilosort 1-3, ``"waveclus"``) and Matlab
#    is installed on your system, you can pass a path to the github downloaded repository
#    of the sorter.
#
# ``"singularity"``:
#    Use singularity to run the sorter in a container. This is useful is you want to
#    run a sorter written in Matlab, but do not have Matlab available on your system.
#    Under the hood, Matlab is installed in the singularity image automatically.
#    Singularity images will be downloaded and saved in a ``sorter_images`` folder at the
#    same level as `rawdata` / `derivatives`. These are expected to be shared across
#    the entire project.
#
# ``"docker"``:
#   Run the sorter in a docker image. The docker client will manage the downloading of sorters.

# %%
# Sorting Configs
# ---------------
#
# A configurations dictionary (see :ref:`Managing Configs <configs-tutorial>`) is structured like:


config_dict = {
    "preprocessing": {
        "1": ["phase_shift", {}],
        "2": ["bandpass_filter", {"freq_min": 300, "freq_max": 6000}],
        "3": ["common_reference", {"operator": "median"}]
    },
    "sorting": {
        "mountainsort5": {}}
}

# %%
# The :class:`spikewrap.Session.sort` function will accept the name
# of the stored config file, the full config dictionary such as above,
# or the "sorting" sub-dictionary, e.g.:

sorting_dict = {"sorting": {"mountainsort5": {}}}

session.sort(
    configs=sorting_dict, run_sorter_method="local"
)

# %%
# The sorter name (e.g. ``"mountainsort5"``) should make the SpikeInterface
# sorter name, while the keyword-arguments should match the sorter-specific arguments.
#
# These can be found at the corresponding soruce code files for the SpikeInterface
# sorter, e.g. ``"kilsoort2_5"``, ``"kilosort4"``, ``"mountainsort5"``, ``"spykingcircus2"``).
