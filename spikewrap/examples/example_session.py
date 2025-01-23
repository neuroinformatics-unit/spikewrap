
import spikewrap as sw

session = sw.Session(
    subject_path=sw.get_example_data_path() / "rawdata" / "sub-001",
    session_name="ses-001",
    file_format="spikeglx"  # or "openephys"
)

session.load_raw_data()

session.preprocess(
    pp_steps="neuropixels",
    per_shank=True,
    concat_runs=True,
)

session.save_preprocessed(overwrite=True, n_jobs=1)
