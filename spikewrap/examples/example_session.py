import spikewrap as sw

if __name__ == "__main__":
    session = sw.Session(
        subject_path=sw.get_example_data_path("spikeglx") / "rawdata" / "sub-001",
        session_name="ses-001",
        file_format="spikeglx",  # or "openephys"
    )

    session.preprocess(
        configs="neuropixels+kilosort2_5",
        per_shank=False,
        concat_runs=False,
    )

    session.plot_preprocessed(show=True)

    session.save_preprocessed(overwrite=True, n_jobs=6, slurm=False)
