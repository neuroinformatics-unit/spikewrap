# ruff: noqa: E402
"""
.. _supported-preprocessing-tutorial:

Supported Preprocessing Steps
=============================

In ``spikewrap``, all preprocessing is performed using
`SpikeInterface <https://spikeinterface.readthedocs.io/en/stable/>`_
under the hood.

In the majority of cases, preprocessing settings in the configuration dictionary
map 1:1 with spikeinterface function names and their arguments.

In a few cases (highlighted below) this is not possible, and these functions are documented below.
In time, the aim will be to transfer all preprocessing into SpikeInterface.
 
As a reminder, an example configuration dictionary is strictured like:
"""
pp_steps = {
    "1": ["phase_shift", {}],
    "2": ["bandpass_filter", {"freq_min": 300, "freq_max": 6000}],
    "3": ["remove_bad_channels", {"detect_bad_channel_kwargs": {"chunk_duration_s": 0.5}}],
    "4": ["common_reference", {"operator": "median"}],
}

# %%
# (see the :ref:`the Managing Configs tutorials <configs-tutorial>` for details).

# %%
# Steps that directly map SpikeInterface
# --------------------------------------
#
# ``phase_shift``
# ^^^^^^^^^^^^^^^
# The name and arguments map directly to SpikeInterface's
# `phase_shift <https://spikeinterface.readthedocs.io/en/latest/api.html#spikeinterface.preprocessing.phase_shift>`_
# function.
#
# ``bandpass_filter``:
# ^^^^^^^^^^^^^^^^^^^^
# The name and arguments map directly to SpikeInterface's
# `bandpass_filter <https://spikeinterface.readthedocs.io/en/latest/api.html#spikeinterface.preprocessing.bandpass_filter>`_
# function.
#
# ``common_reference``:
# ^^^^^^^^^^^^^^^^^^^^^
# The name and arguments map directly to SpikeInterface's
# `common_reference <https://spikeinterface.readthedocs.io/en/latest/api.html#spikeinterface.preprocessing.common_reference>`_
# function.
#
# ``whiten``:
# ^^^^^^^^^^^
# The name and arguments map directly to SpikeInterface's
# `whiten <https://spikeinterface.readthedocs.io/en/latest/api.html#spikeinterface.preprocessing.whiten>`_
# function.

# %%
# Steps that do not directly map SpikeInterface
# ---------------------------------------------
#
# While these steps use SpikeInterface under the hood, they do not map 1:1 to
# the SpikeInterface API.
#
# For reference, their implementations are in ``spikewrap.process._preprocessing``
# (however, they should not be called directly, instead use the config_dict as above).
#
# .. note::
#     Currently, bad-channel detection is performed per-run (if not concatenated). In some cases it is useful
#     to remove the union of all bad channels (across runs from each run). This is not currently implemented in
#     spikewrap, but if you would like to use this, please get in contact.
#
# .. warning::
#     Bad-channel detection is performed at the :class:`spikewrap.Session.preprocess` stage,  and so may slow down
#     this call. This is in contract to other preprocessing steps which are lazy.
#
# ``remove_bad_channels``
# ^^^^^^^^^^^^^^^^^^^^^^^
#
# This function removes bad channels from the recording. Under the hood it uses SpikeInterface's
# `detect_bad_channels <https://spikeinterface.readthedocs.io/en/latest/api.html#spikeinterface.preprocessing.detect_bad_channels>`_
# and `remove_channels <https://spikeinterface.readthedocs.io/en/latest/modules/preprocessing.html#detect-bad-channels-interpolate-bad-channels>`__ functions.
# The default settings use the International Brain Laboratory's (IBLs)
# `detect bad channels approach <https://figshare.com/articles/online_resource/Spike_sorting_pipeline_for_the_International_Brain_Laboratory/19705522?file=49783080>`_. It's parameters are:
#
# * ``labels_to_remove``: Set the bad-channel labels to remove. During bad channel detection, channels are labelled ``"good"``, ``"out"`` (of brain), ``"noise"`` and ``"dead""``. This argument removes channels that have the passed labels. e.g. ``["noise", "dead"]`` will remove only dead and noisy channels, but out of brain and good channels will be retained.
# * ``detect_bad_channel_kwargs``: A dictionary of arguments that will be passed to SpikeInterface's `detect_bad_channels <https://spikeinterface.readthedocs.io/en/latest/api.html#spikeinterface.preprocessing.detect_bad_channels>`_.
#
# ``interpolate_bad_channels``
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#
# This function interpolates (Kriging) bad channels in the recording. Under the hood it uses SpikeInterface's
# `detect_bad_channels <https://spikeinterface.readthedocs.io/en/latest/api.html#spikeinterface.preprocessing.detect_bad_channels>`__ and
# `interpolate_bad_channels <https://spikeinterface.readthedocs.io/en/latest/modules/preprocessing.html#detect-bad-channels-interpolate-bad-channels>`__ function.
# Note that the spikeinterface ``interpolate_bad_channels`` only interpolates a given list of channels, rather than the detect-and-interpolate performed in ``spikewrap``.
# The default method uses the International Brain Laboratory's (IBLs)
# `detect bad channels approach <https://figshare.com/articles/online_resource/Spike_sorting_pipeline_for_the_International_Brain_Laboratory/19705522?file=49783080>`_
#
# * ``labels_to_remove``: Set the bad-channel labels to interpolate. During bad channel detection, channels are labelled ``"good"``, ``"out"`` (of brain), ``"noise"`` and ``"dead""``. This argument interpolates channels that have the passed labels. e.g. ``["noise", "dead"]`` will interpolate only dead and noisy channels, but out of brain and good channels will be retained.
# * ``detect_bad_channel_kwargs``: A dictionary of arguments that will be passed to SpikeInterface's `detect_bad_channels <https://spikeinterface.readthedocs.io/en/latest/api.html#spikeinterface.preprocessing.detect_bad_channels>`_.
# * ``interpolate_bad_channel_kwargs``: A dictionary of kwargs that will be passed to SpikeInterface's `interpolate_bad_channels <https://spikeinterface.readthedocs.io/en/latest/modules/preprocessing.html#detect-bad-channels-interpolate-bad-channels>`__ function that performs the interpolation (but not detection).
#
# ``remove_channels``
# ^^^^^^^^^^^^^^^^^^^
#
# This function to remove a given list of channels from the recording.
# Uses SpikeInterface's `whiten <https://spikeinterface.readthedocs.io/en/latest/api.html#spikeinterface.preprocessing.whiten>`__ function.
#
# * ``channel_ids``: A list of channel ids to remove from the recording.
#
# ``interpolate_channels``
# ^^^^^^^^^^^^^^^^^^^^^^^^
#
# This function to interpolate (Kriging) a given list of channels in the recording.
# Uses SpikeInterface's `interpolate_bad_channels <https://spikeinterface.readthedocs.io/en/latest/api.html#spikeinterface.preprocessing.whiten>`__ function.
#
# * ``channel_ids``: A list of channel ids to interpolate.
# * ``interpolate_bad_channel_kwargs``: A dictionary of kwargs that will be passed to SpikeInterface's `interpolate_bad_channels <https://spikeinterface.readthedocs.io/en/latest/modules/preprocessing.html#detect-bad-channels-interpolate-bad-channels>`__ function that performs the interpolation (but not detection).
#



