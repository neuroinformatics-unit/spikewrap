# ruff: noqa: E402
"""
.. _sorting-howto:

How  to run Spike Sorting
=========================

.. note::
    This is a quick how-to on spike sorting. See :ref:`here <sorting-tutorial>` for a long-form tutorial.

"""

# %%
#

import spikewrap as sw

session = sw.Session(
    subject_path=sw.get_example_data_path() / "rawdata" / "sub-001",
    session_name="ses-001",
    file_format="spikeglx",  # or "openephys"
    run_names="all"
)

session.preprocess(
    configs="neuropixels+mountainsort5",
    concat_runs=True  # concatenate runs before preprocessing
)

# Optional: session.save_preprocessed(overwrite=True)
# The sorting is run with data generated in the most recent
# `preprocess()` call, even if data is saved.
# If `preprocess()` is not called, saved data will be used.

session.sort(
    "neuropixels+mountainsort5",
    run_sorter_method="local",  # or a path to matlab repository, "singularity" or "docker"
    per_shank=True,
    concat_runs=False,  # concatenate runs before sorting
)