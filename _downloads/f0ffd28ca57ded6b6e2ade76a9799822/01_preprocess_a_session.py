# ruff: noqa: E402
"""
.. _preprocess-session-howto:

How to preprocess a session
===========================

.. note::
    This is a quick how-to on session preprocessing. See :ref:`here <preprocess-session-tutorial>` for a long-form tutorial.

"""
if __name__ == "__main__":  # for multiprocessing

    import spikewrap as sw

    # We will use these configs
    sw.show_configs("neuropixels+kilosort2_5")

    # Now we will preprocess and save all sesssion data.

    session = sw.Session(
        subject_path=sw.get_example_data_path() / "rawdata" / "sub-001",
        session_name="ses-001",
        file_format="spikeglx",  # or "openephys"
        run_names="all"
    )

    session.load_raw_data()

    session.preprocess(
        configs="neuropixels+kilosort2_5",
        per_shank=True,
        concat_runs=True
    )

    plots = session.plot_preprocessed(
        show=True,
        time_range=(0, 0.5),
        show_channel_ids=False,  # also, "mode"="map" or "line"
    )

    session.save_preprocessed(overwrite=True, n_jobs=6, slurm=False)

# %%
# We could run again with different configs and multiprocessing:

if __name__ == "__main__":

    pp_steps = {
        "1": ["bandpass_filter", {"freq_min": 300, "freq_max": 6000}],
        "2": ["common_reference", {"operator": "median"}],
    }

    session.preprocess(configs=pp_steps, per_shank=False, concat_runs=False)

    session.plot_preprocessed(
        show=True,
        time_range=(0, 0.5),
        show_channel_ids=False,  # also, "mode"="map" or "line"
    )

    session.save_preprocessed(overwrite=True, n_jobs=6, slurm=False)