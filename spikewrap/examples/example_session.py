import spikewrap as sw

if __name__ == "__main__":

    # Make up a probe for this recording
    session = sw.Session(
        subject_path=sw.get_example_data_path("spikeglx") / "rawdata" / "sub-001",
        session_name="ses-001",
        file_format="spikeglx",
    )

    # TODO: document well the class lifespan
    #   session.preprocess(
    #       configs="neuropixels+kilosort2_5",
    #       per_shank=True,
    #       concat_run=True,
    #   )

    #  session.plot_preprocessed(
    #      run_idx="all", mode="map", show_channel_ids=False, show=True, figsize=(12, 8)
    #  )

    #  session.save_preprocessed(
    #      overwrite=True, n_jobs=1, slurm=False, chunk_duration_s=0.1
    #  )

    # 1) figure out what will happen for all per_shank, concat_run combinations
    # 2) figure out slurm
    # 3) figure out overwrite
    # 4) figure out run_method

    # TODO: properly test runs and stuff
    # 1) make a test script for singularity
    # 2) and docker
    # 3) and matlab
    # 4) and ofc local
    # TODO: check there is a warning when per_shank is on for prepro and off for sorting. maybe raise?
    session.sort(
        configs="neuropixels+mountainsort5",
        run_sorter_method="local",  # "local", "singularity", "docker" or path to MATLAB install (check for mex files!)
        per_shank=False,
        concat_run=False,
        overwrite=True,
        slurm=False,
    )

    """
8)  handle existing preprocessing, loading into preprocessing etc.
    """
