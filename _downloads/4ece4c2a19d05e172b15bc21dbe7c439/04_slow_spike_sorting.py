# ruff: noqa: E402
"""
.. _sorting-tutorial:

Spike Sorting
=============

.. note::
    This is a long-form tutorial on sorting. See :ref:`here <sorting-howto>` for a quick how-to.

"""

# %%
# Running Sorting after Preprocessing
# -----------------------------------
#
# Spike sorting can be run on preprocessed data, even without saving to disk,
# using the :class:`spikewrap.Session.sort` function.
#
# This wraps `SpikeInterface's <https://spikeinterface.readthedocs.io/en/stable/>`_,
# module. The list of available sorters can be found in
# `their documentation. <https://spikeinterface.readthedocs.io/en/stable/modules/sorters.html#supported-spike-sorters>`_
#
# For example, to run spike sorting after preprocessing (without saving the preprocessed data to disk):

import spikewrap as sw

session = sw.Session(
    subject_path=sw.get_example_data_path() / "rawdata" / "sub-001",
    session_name="ses-001",
    file_format="spikeglx",  # or "openephys"
    run_names="all"
)

session.preprocess(
    configs="neuropixels+mountainsort5",
    per_shank=False,
    concat_runs=True
)

session.sort(
    "neuropixels+mountainsort5",
    run_sorter_method="local",
    per_shank=True,
    concat_runs=False,
)

# %%
#
# Sorting results are output to a folder called ``sorting`` in the run's output folder:
#
# .. code-block::
#
#     └── my_project/
#         └── derivatives/
#             └── sub-001  /
#                 └── ses-001/
#                     └── ephys/
#                         ├── concat_run/
#                         │   ├── preprocessed/
#                         │   │   └── <preprocessed_data>
#                         │   └── sorting/
#                         │       └── shank_0
#                         │           └── ...
#                         │       └── shank_1
#                         │           └── ...
#                         └── ...
#
# The ``per_shank`` and ``concat_runs`` arguments on the ``sort`` function
# indicate whether the recording should be split per shank or concatenated
# prior to sorting. If the recording has already been split-by-shank
# and / or concatenated at the preprocessing stage, they will remain so for sorting.
#
# In the example above, runs are concatenated before preprocessing and then the
# concatenated run is sorted. The shanks are preprocessed together, and then
# split before sorting.
#
# See :ref:`Sorting Configs <sorting-configs>` below for information on
# how to select and configure the sorter to use.
#
# Running Sorting from Saved Preprocessing
# ----------------------------------------
#
# Alternatively, the preprocessed data might be saved prior to sorting.
# In this case, sorting can be run directly from the saved data.
# For example, first preprocessed recordings are saved:

session = sw.Session(
    subject_path=sw.get_example_data_path() / "rawdata" / "sub-001",
    session_name="ses-001",
    file_format="spikeglx",  # or "openephys"
    run_names="all"
)

session.preprocess(
    configs="neuropixels+mountainsort5", concat_runs=True
)

session.save_preprocessed(overwrite=True)

# %%
# In a new session, the sorting can be run directly, and will be loaded
# from the previously saved preprocessed data:

session = sw.Session(
    subject_path=sw.get_example_data_path() / "rawdata" / "sub-001",
    session_name="ses-001",
    file_format="spikeglx",
    run_names=["concat_run"]
)

# Here, the preprocessed data will be detected and loaded from disk, if available.
# Otherwise, an error will be raised.

session.sort(
    configs="neuropixels+mountainsort5", run_sorter_method="local"
)

# %%
# .. warning::
#
#    If preprocessing is run in memory, it will take precedence over previously
#    saved preprocessed runs. The preprocessed data generated on the last call
#    to :class:`spikewrap.Session.preprocess` will be used for sorting, even if saved data exists.
#
#    For example:
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
# ----------------------
#
# The ``run_sorter_method`` argument specifies the method used to run the sorter.
# These are based on the extensive options provided by the SpikeInterface package,
# which provide great flexibility in ways that sorters can be run. The options are:
#
# ``"local"``:
#   Used if the sorter can be run in the current python environment,
#   (i.e. it is a sorter written in Python, such as ``"kilosort4"`` or ``"spykingcircus2"``).
#
# A ``Path`` object:
#    A path to the sorter repository, if the sorter is written in Matlab (e.g. kilosort 1-3, ``"waveclus"``)
#    and Matlab is installed on your system. For example, to run kilosort 2.5 download
#    `their repository <https://github.com/MouseLand/Kilosort/tree/kilosort25>`_ (note the branch is changed
#    to '`kilosort25`') then pass a path to the ``Kilosort`` directory.
#
# ``"singularity"``:
#    Use singularity to run the sorter in a container. This is useful is you want to
#    run a sorter written in Matlab, but do not have Matlab available on your system.
#    Under the hood, Matlab is pre-installed in the singularity image.
#    Singularity images will be downloaded and saved in a ``sorter_images`` folder at the
#    same level as ``rawdata`` / ``derivatives``. Download is only required once, then the images
#    shared across the entire project.
#
# ``"docker"``:
#   Run the sorter in a docker image. The docker client will manage the downloading of sorters.


# %%
# Sorting Configs
# ---------------
# .. _sorting-configs:
#
# A configurations dictionary (see :ref:`Managing Configs <configs-tutorial>`) is structured like:


config_dict = {
    "preprocessing": {
        "1": ["phase_shift", {}],
        "2": ["bandpass_filter", {"freq_min": 300, "freq_max": 6000}],
        "3": ["common_reference", {"operator": "median"}]
    },
    "sorting": {
        "mountainsort5": {"filter": False}}
}

# %%
# The :class:`spikewrap.Session.sort` function will accept the name
# of the stored config file, the full config dictionary such as above,
# or the "sorting" sub-dictionary, e.g.:
#
# .. code-block:: python
#
#     sorting_dict = {"sorting": {"mountainsort5": {"filter": False}}}
#
#     session.sort(
#         configs=sorting_dict, run_sorter_method="local"
#     )
#

# %%
# The sorter name (e.g. ``"mountainsort5"``) should make the
# `SpikeInterface sorter name <https://spikeinterface.readthedocs.io/en/latest/modules/sorters.html#supported-spike-sorters>`_,
# while the keyword-arguments should match the sorter-specific arguments.These can be found at the
# corresponding source code files for the SpikeInterface sorter, e.g.
# `kilsort2_5 <https://github.com/SpikeInterface/spikeinterface/blob/697058eb528394f89ae4b5d03aa56c1ba3ec9db2/src/spikeinterface/sorters/external/kilosort2_5.py#L32>`_,
# `kilsort4 <https://github.com/SpikeInterface/spikeinterface/blob/697058eb528394f89ae4b5d03aa56c1ba3ec9db2/src/spikeinterface/sorters/external/kilosort4.py#L18>`_,
# `mountainsort5 <https://github.com/SpikeInterface/spikeinterface/blob/697058eb528394f89ae4b5d03aa56c1ba3ec9db2/src/spikeinterface/sorters/external/mountainsort5.py#L18>`_ or
# `spykingcircus2" <https://github.com/SpikeInterface/spikeinterface/blob/697058eb528394f89ae4b5d03aa56c1ba3ec9db2/src/spikeinterface/sorters/internal/spyking_circus2.py#L23>`_.
#