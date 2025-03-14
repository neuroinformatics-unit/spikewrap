# ruff: noqa: E402
"""
.. _preprocess-session-tutorial:

Supported Preprocessing Steps
=============================

In ``spikewrap``, all preprocessing is performed using SpikeInterface
under the hood. In the majority of cases, arguments to the config dictionary
map 1:1 with spikeinterface function names and their arguments. In a few cases
(highlighted below) this is not possible, however the aim is to transfer all
preproecssing into SpikeInterface as soon as possible)
 
As a reminder, an example dictionary looks lke the below, please
see XXX for more detail on configs: 
"""
pp_steps = {
    "1": ["phase_shift", {}],
    "2": ["bandpass_filter", {"freq_min": 300, "freq_max": 6000}],
    "3": ["remove_bad_channels", {"detect_bad_channel_kwargs": {"chunk_duration_s": 0.5}}],
    "4": ["common_reference", {"operator": "median"}],
}

# %%
# Steps that directly map SpikeInterface
# -------------------------------------
# ``phase_shift``
# : hello world
#
# ``bandpass_filter``
# : hello world
#
# ``common_reference``
# :
#
# ``whiten``
# :
#
# %%
# Steps that do not directly map SpikeInterface
# ---------------------------------------------
#
# While these steps use SpikeInterface under the hood, they do not map 1:1 to
# the SpikeInterface API.
#
# For reference, their implementations are in spikewrap.process.preprocessing
# and their arguments are maintained in the API documentation (linked below).
# However, they should not be called directly, instead use the config_dict.
#
# ``remove_bad_channels``
# : This function removes
#
# ``interpolate_bad_channels``
# :
#
#
# ``remove_channels``
#
# ``interpolate_channels``
#
#






