import spikewrap as sw

if __name__ == "__main__":

    # Make up a probe for this recording
    session = sw.Session(
        subject_path=sw.get_example_data_path("spikeglx") / "rawdata" / "sub-001",
        session_name="ses-001",
        file_format="spikeglx",
    )

    session.preprocess(
        configs="neuropixels+mountainsort5",
        per_shank=True,
        concat_runs=False,
    )

    session.plot_preprocessed(
        run_idx="all",
        mode="map",
        show_channel_ids=False,
        show=True,
        figsize=(12, 8),
    )

    session.save_preprocessed(
        overwrite=True,
        n_jobs=1,
        slurm=True,
        chunk_duration_s=0.1,
    )

    session.sort(
        configs="neuropixels+mountainsort5",
        run_sorter_method="local",
        per_shank=False,
        concat_runs=False,
        overwrite=True,
        slurm=False,
    )
