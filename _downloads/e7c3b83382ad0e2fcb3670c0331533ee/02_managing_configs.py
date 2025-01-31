# ruff: noqa: E402
"""
.. _configs-tutorial:

Managing ``configs``
====================

.. note::
    This is a long-form tutorial on ``config`` management. See :ref:`here <configs-howto>` for a quick how-to.

In ``spikewrap``, ``configs`` encode the preprocessing and sorting settings for a pipeline.
The emphasis is on convenient sharing of pipelines, while allowing flexibility for prototyping.

All ``configs`` in ``spikewrap`` map directly to underlying
`SpikeInterface functions <https://spikeinterface.readthedocs.io/en/stable/api.html>`_.

To use the ``configs``, they are passed to processing functions (e.g. :class:`spikewrap.Session.preprocess`),
in one of three ways:

**config name**:
    A keyword to a saved confgiuration e.g. ``"neuropixels+kilosort2_5"`` (this comes with ``spikewrap``).
**dictionary**:
    A ``dict`` with ``"preprocessing"`` and ``"sorting"`` keys (more details below).
**.yaml**:
    A YAML file, which is the ``configs`` dictionary dumped to file.

In this tutorial we will cover how to run processing steps with configs,
as well as how to make, share and save your own pipelines.

"""

# %%
# ``configs`` as a name
# ---------------------
# The easiest way to manage already-established ``configs`` is to
# pass a keyword that refers to a previously saved pipeline.
#
# For example, we can use the ``"neuropixels+kilosort2_5"``  in :class:`spikewrap.Session.preprocess`:
#
# .. code-block:
#
#     session.preprocess("neuropixels+kilosort2_5", ...)
#
# and print the underlying steps with:

import spikewrap as sw

sw.show_configs("neuropixels+kilosort2_5")

# %%
# It is possible to create and share your own keyword configs. Under the hood,
# these are ``.yaml`` files that hold a python dictionary representation of the steps.
# These are stored in a dedicated path, (``.spikewrap`` in your user directory), which
# you can find with:

sw.get_configs_path()

# %%
# and see what configs you have available at this path:

sw.show_available_configs()

# %%
# Continue reading below to create and save your own pipeline configs.

# %%
# ``configs`` as a dictionary
# ---------------------------
# Custom preprocessing and sorting settings can be defined in a dictionary,
# with the keys ``preprocessing`` and ``sorting``.

config_dict = {
    "preprocessing": {
        "1": ["phase_shift", {}],
        "2": ["bandpass_filter", {"freq_min": 300, "freq_max": 6000}],
        "3": ["common_reference", {"operator": "median"}]
    },
    "sorting": {
        "kilosort2_5": {'car': False, 'freq_min': 150}}
}

# use like:
# session.preprocess(configs=config_dict, ...)

# %%
# .. dropdown:: ``configs`` dictionary structure
#
#     The structure of a ``configs`` dictionary is :
#       1. The first level is keys ``"preprocessing"`` and ``"sorting"``
#       2. The ``"preprocessing"`` value is a dictionary with string keys,
#          with each a number (starting at ``"1"`` and increasing by 1) indicating the order of the preprocessing step.
#       3. The value of each preprocessing step is a list, in which the first entry is
#          he preprocessing step to run, and the second a dictionary of keyword arguments
#          to pass to the function. The preprocessing step name must refer to a
#          `SpikeInterface <https://spikeinterface.readthedocs.io/en/stable/api.html>`_. preprocessing function.
#
# Each preprocessing step and arguments map directly onto the underlying
# `SpikeInterface functions <https://spikeinterface.readthedocs.io/en/stable/api.html>`_.
#
# To see the currently available preproecssing steps supported by ``spikewrap``, run:

sw.show_supported_preprocessing_steps()

# %%
# This configs dict can be saved by ``spikewrap`` along with
# a name. Then, this name can be used for in future processing steps.

sw.save_config_dict(config_dict, "my_config")

# and then:
# session.preprocess(configs="my_config", ...)

# %%
# ``configs`` as a YAML file
# --------------------------
#
# When the `configs`` dictionary is saved, it is saved as a `.yaml` file.

sw.save_config_dict(config_dict, "my_config")

# %%
# By default, this will be written to the ``spikewrap`` storage path so
# ``"my_config"`` can be used in ``spikewrap`` processing steps, as above.
#
# Use :func:`spikewrap.get_configs_path` to get the path where these are stored.
#
# Alternatively, this can be output to a path of your choice:
#
# .. code-block::
#
#    sw.save_config_dict(config_dict, "my_config", folder="...path_to_folder")
#
# If you have received a pipeline you would like to use, you can load the dictionary, and
# then save it the ``spikewrap`` config store for easy use:
#
# .. code-block::
#
#    config_dict = sw.load_config_dict("...path_to_colleagues_config.yaml")
#    sw.save_config_dict(config_dict, "colleague_xs_pipeline")
#
#    # Can now run:
#    # session.preprocess(configs="colleague_xs_pipeline")
#
# Passing a YAML as a file path
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ``spikewrap`` functions will take a path to any valid ``configs`` ``.yaml`` file
#
# .. code-block::
#
#     session.preprocess(config=".../my_config.yaml")

# %%
# and we can load ``configs`` from file:

config_dict = sw.load_config_dict(
    sw.get_configs_path() / "neuropixels+kilosort2_5.yaml"
)

import json  # use for printing dicts
print(json.dumps(config_dict, indent=4))

