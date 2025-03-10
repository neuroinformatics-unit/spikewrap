import spikewrap as sw

if __name__ == "__main__":

    # Make up a probe for this recording
    session = sw.Session(
        subject_path=sw.get_example_data_path("openephys") / "rawdata" / "sub-001",
        session_name="ses-001",
        file_format="openephys",
    )

    session.load_raw_data()

    print(session.get_sync_channel(run_idx=0))
    session.plot_sync_channel(run_idx=0)
    session.silence_sync_channel(run_idx=0, periods_to_silence=[(0, 500)])
    session.plot_sync_channel(run_idx=0)
    print(session.get_sync_channel(run_idx=0))

    if False:
        session.preprocess(
            configs="neuropixels+mountainsort5",
            per_shank=True,
            concat_runs=True,
        )

        session.plot_preprocessed(
            run_idx="all",
            mode="map",
            show_channel_ids=False,
            show=True,
            figsize=(12, 8),
        )

        session.save_preprocessed(
            overwrite=True, n_jobs=1, slurm=False, chunk_duration_s=0.1
        )

        session.sort(
            configs="neuropixels+mountainsort5",
            run_sorter_method="local",
            per_shank=False,
            concat_runs=False,
            overwrite=True,
            slurm=False,
        )
