import spikewrap as sw

if __name__ == "__main__":
    session = sw.Session(
        subject_path=sw.get_example_data_path("openephys") / "rawdata" / "sub-001",
        session_name="ses-001",
        file_format="openephys",  # "spikeglx" or "openephys"
    )

    session.preprocess(
        configs="neuropixels+kilosort2_5",
        per_shank=False,
        concat_runs=False,
    )

    session.plot_preprocessed(
        run_idx="all", mode="map", show_channel_ids=False, show=True, figsize=(12, 8)
    )

    session.save_preprocessed(
        overwrite=True, n_jobs=1, slurm=False, chunk_duration_s=0.1
    )
