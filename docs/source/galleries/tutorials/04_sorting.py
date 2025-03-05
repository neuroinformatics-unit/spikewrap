# ruff: noqa: E402
"""
.. _slurm-tutorial:

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
# The `per_shank` and `concat_runs` arguments indicate whether
# the recording should be split per shank or concatenated
# prior to sorting. If the recording has already been split-by-shank
# and / or concatenated before preprocessing, they will remain so for sorting.
#
# The `run_sorter_method` indicates the method used to run the sorter.
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
    run_names=["concat_run"]  # run names to sort TODO CHECK THIS IS NOT A STR IF NOT ALL ALSO TODO YOU CAN HAVE MIXED PP RUNS WHEN LOADING FROM DISK!! 
)

# Here, the preprocessed data will be detected and loaded from disk, if available.
# Otherwise, an error will be raised.

# TODO: why does this not raise if no save data done? TODO: review and add asserts

session.sort(
    configs="neuropixels+mountainsort5", run_sorter_method="local"
)


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
#
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
#
# sorting_dict = {"sorting: {"mountainsort5": {}}"
#
# The sorter name (e.g. "mountainsort5") should make the SpikeInterface
# sorter name, while the keyword-arguments should match the sorter-specific arguments.
#
# These can be found at the corresponding soruce code files for the SpikeInterface
# sorter, e.g. kilsoort2_5, kilosort4, mountainsort5, spykingcircus2).
