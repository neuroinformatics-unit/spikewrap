from spikewrap.structure.session import Session

# TODO: print a load of stuff!

# TODO: check why si cannot open openephys test files

# TODO: take name from path if name not set? just path!
session = Session(
    subject_path = r"C:\Users\Jzimi\git-repos\spikewrap\test_data\spikeglx\rawdata\1119617",
    session_name="1119617_LSE1_shank12_g0",
    file_format="spikeglx",
    run_names="all",
)

session.get_run_names()

# reload raw data each time, from fresh! allows fast iteration
session.preprocess(
    config="neuropixels",
    per_shank=True,
    concat_runs=True
    # also output QM...
)

session.plot_preprocessed(show=True, time_range=(0, 2))  # remove the show and save, just return the plot! then do this internally for save_preprocessed

session.save_preprocessed(overwrite=True, chunk_size=None, slurm=False)  # TODO: n_jobs

# session.plot_preprocessed({}, show=True, save=True)  REMOVE SAVE

# session.plot_preprocessing_steps({}, show=True, save=True)

# crash if already exists, allow to pass `derivatives_path` hmm
# session.save_preprocessed(overwrite=True, chunk_size=None)

# session.plot_raw()

# session.plot_preprocessed()

# session.plot_preprocessing_steps()

# session.sort()




if False:
    session.load()
    session.preprocess(

    )