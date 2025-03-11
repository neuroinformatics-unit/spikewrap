# ruff: noqa: E402
"""
.. _sync-channel-howto:

How to Edit the Sync Channel
============================

.. note::
    This is a quick how-to on working with the sync channel. See :ref:`here <sync-channel-tutorial>` for a long-form tutorial.

"""

# %%
# .. warning::
#     Currently, the only supported sync channel is for Neuropixels data (in which it is
#     the 385th channel). Please get in contact to see other cases supported.


import spikewrap as sw

session = sw.Session(
    subject_path=sw.get_example_data_path("openephys") / "rawdata" / "sub-001",
    session_name="ses-001",
    file_format="openephys",
    run_names="all"
)

session.load_raw_data()

session.get_raw_run_names()

# get the sync channel data as a numpy array
run_1_sync_channel = session.get_sync_channel(run_idx= 0)

# or plot the sync channel
session.plot_sync_channel(run_idx=0, show=True)

# edit the sync channel
session.silence_sync_channel(
    run_idx=0,
    periods_to_silence=[(0, 250), (500, 750)]
)

# refresh the sync channel
session.load_raw_data(overwrite=True)

# The sync channel can be concatenated as part of the preprocessing
session.preprocess("neuropixels+kilosort2_5", concat_runs=True)

# the sync channel will only change after preprocessing if concatenation is used.
concat_sync_channel = session.get_sync_channel_after_preprocessing(run_idx=0)

# this is the sync channel that is saved with `save_preprocessed`:
session.save_preprocessed(overwrite=True)