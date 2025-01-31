# ruff: noqa: E402
"""
.. _configs-howto:

How to manage ``configs``
=========================

.. note::
    This is a quick how-to on ``config`` management. See :ref:`here <configs-tutorial>` for a long-form tutorial.

"""

# %%
# Show available ``configs``

import spikewrap as sw

sw.show_configs("neuropixels+kilosort2_5")

# %%

print(f"These are stored at:\n"
      f"{sw.get_configs_path()}")

# %%
# We can create and save our own ``configs``, from the currently supported steps.

sw.show_supported_preprocessing_steps()

# %%
# By default, these will be stored in the spikewrap configs folder (otherwise, pass the
# full filepath to where you want to save a ``.yaml`` file). This config can now be
# used by name in ``spikewrap`` processing functions.

config_dict = {
    "preprocessing": {
        "1": ["phase_shift", {}],
        "2": ["bandpass_filter", {"freq_min": 300, "freq_max": 6000}],
        "3": ["common_reference", {"operator": "median"}]
    },
    "sorting": {
        "kilosort2_5": {'car': False, 'freq_min': 150}}
}

sw.save_config_dict(config_dict, "my_config")

# %%
# or load a ``config`` directly from ``.yaml``

config_dict = sw.load_config_dict(
    sw.get_configs_path() / "neuropixels+kilosort2_5.yaml"
)

# %%
# use :func:`spikewrap.save_config_dict` to save this to the spikewrap with
# a keyword name, to use by name in processing functions.