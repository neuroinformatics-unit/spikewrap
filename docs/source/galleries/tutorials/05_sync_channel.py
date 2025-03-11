# ruff: noqa: E402
"""
.. _sync-channel-tutorial:

Sync Channel Tutorial
=====================

.. note::
    This is a long-form tutorial on sorting. See :ref:`here <sync-channel-howto>` for a quick how-to.

"""
# %%
# .. warning::
#     Currently, the only supported sync channel is from Neuropixels Imec stream
#     (in which it is the 385th channel). Please get in contact to see other cases supported.
#
# Sync channels are used in extracellular electrophysiology to coordinate timestamps
# from across acquisition devices.
#
# In ``spikewrap``, the sync channel can be inspected and edited. **This step
# must be performed prior to preprocessing**, after which the sync channel
# is split from the recording for saving.

# %%
# Inspecting the sync channel
# ---------------------------
#
# The sync channel data can be obtained as a numpy array, or plot.
# Raw data must be loaded prior to working with the sync channel.
# The sync channel for a particular run is specified with the ``run_idx``
# parameter. Runs are accessed in the order they are loaded (as specified
# with ``run_names``, see :class:`spikewrap.Session.get_raw_run_names`.
#
# In this toy example data, the sync channel is set to all ones (typically,
# it would be all ``0`` interspersed with ``1`` indicating triggers).

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
plot = session.plot_sync_channel(run_idx=0, show=True)  # TODO: accept the plot and explain. also explain the results


# %%
# Zeroing out the sync channel
# -------------------------------
#
# The sync channel can be edited to remove triggers by setting periods of
# the sync channel to zero:

session.silence_sync_channel(
    run_idx=0,
    periods_to_silence=[(0, 250), (500, 750)]
)

# %%
# The function takes a list of 2-tuples, where the entries
# indicate the start and end of the period to zero (in samples).
#
# Under the hood this uses the spikeinterface function
# `silence_periods() <https://spikeinterface.readthedocs.io/en/latest/api.html#spikeinterface.preprocessing.silence_periods>`_,
# to zero-out sections of the sync channel.
#
# After plotting the edited sync channel, we see that the periods
# defined above have been zeroed out:

plot = session.plot_sync_channel(run_idx=0, show=True)

# %%
# Refreshing the sync channel
# ---------------------------
#
# To undo any changes made to the sync-channel, the raw data
# can be reloaded:
#
session.load_raw_data(overwrite=True)

# The sync channel is back to original (silenced periods removed)
plot = session.plot_sync_channel(run_idx=0, show=True)

# %%
# Concatenating the sync channel
# ------------------------------
#
# If runs are concatenated during preprocessing, the sync channel
# will be concatenated. To see the sync channel after preprocessing,
# use the function :class:`spikewrap.Session.get_sync_channel_after_preprocessing`.
#
# Note that the sync channel itself is never preprocessed, and in the case
# that concatenation is not performed, the sync channel on a preprocessed
# run will be the same as the sync channel before preprocessing is performed.
#
# The only difference is that if runs were concatenated before preprocessing,
# the sync channel will now reflect this. In the below example, the sync channel
# is now 2000 samples long (each run is 1000 samples long):

session.preprocess("neuropixels+kilosort2_5", concat_runs=True)

concat_sync_channel = session.get_sync_channel_after_preprocessing(run_idx=0)

import matplotlib.pyplot as plt

plt.plot(concat_sync_channel)
plt.show()

# %%
# This is the sync channel that will be saved when :class:`spikewrap.Session.save_preprocessed` is called.

# %%
# Saving the sync channel
# -----------------------
#
# The easiest way to manage sync channel saving is to let spikewrap save the sync
# channel as part of :class:`spikewrap.Session.save_preprocessed`. Otherwise, it can get saved
# manually after obtaining it from a getter function.
#
# .. note::
#     Currently, the sync channel is saved after preprocessing, but not sorting. Therefore,
#     if concatenating runs before sorting, this will not be reflected in the sync channel.
#     Please get in contact if you would like to see this implemented.
#





