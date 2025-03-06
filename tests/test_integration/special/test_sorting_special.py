from __future__ import annotations

import spikewrap as sw

DATA_SUB_PATH = r"/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/code/git-repos/SPIKEWRAP_TESTS/data/time-short/rawdata/1119617"
KILOSORT2_5_PATH = "/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/code/git-repos/SPIKEWRAP_TESTS/matlab_repos/kilosort2_5/Kilosort"

KILOSORT2_5_PATH_NOMEX = "/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/code/git-repos/SPIKEWRAP_TESTS/matlab_repos/kilosort2_5_nomex/Kilosort"

# class TestSortingSpecial():


def test_kilosort4_local():

    session = sw.Session(
        subject_path=DATA_SUB_PATH,
        session_name="ses-001",
        file_format="spikeglx",
    )

    # TODO: document well the class lifespan
    session.preprocess(
        configs="neuropixels+kilosort2_5",  # TODO: neuropixels+kilsort... allow possible ones, then choose sorter....
        per_shank=True,
        concat_runs=True,
    )

    config_dict = {"kilosort4": {}}
    session.sort(config_dict, "local")


# @pytest.mark.parametrize("slurm", [True, False])
def test_kilosort2_5_path(slurm=True):

    session = sw.Session(
        subject_path=DATA_SUB_PATH,
        session_name="ses-001",
        file_format="spikeglx",
    )

    # TODO: document well the class lifespan
    session.preprocess(
        configs="neuropixels+kilosort2_5",  # TODO: neuropixels+kilsort... allow possible ones, then choose sorter....
        per_shank=True,
        concat_runs=True,
    )

    config_dict = {"kilosort2_5": {}}

    gpu_arguments = sw.default_slurm_options("gpu")

    gpu_arguments["mem_gb"] = 60
    gpu_arguments["env_name"] = "dammy-test"
    gpu_arguments["exclude"] = None
    print(gpu_arguments)
    session.sort(
        config_dict,
        KILOSORT2_5_PATH,
        slurm=False,  # gpu_arguments  # TODO: handle when to require GPU node!
    )


def test_kilosort2_5_nomex():
    session = sw.Session(
        subject_path=DATA_SUB_PATH,
        session_name="ses-001",
        file_format="spikeglx",
    )

    # TODO: document well the class lifespan
    session.preprocess(
        configs="neuropixels+kilosort2_5",
        # TODO: neuropixels+kilsort... allow possible ones, then choose sorter....
        per_shank=True,
        concat_runs=True,  # TODO: just run on a single run
    )

    config_dict = {"kilosort2_5": {}}

    gpu_arguments = sw.default_slurm_options("gpu")

    gpu_arguments["mem_gb"] = 60
    gpu_arguments["env_name"] = "dammy-test"
    gpu_arguments["exclude"] = None

    session.sort(
        config_dict,
        KILOSORT2_5_PATH_NOMEX,
        slurm=False,  # gpu_arguments
        # TODO: handle when to require GPU node!
    )

    # TODO: mutlipel slurm jobs one after the other will try and write to the same place!!! need to make sure past slurm job is finished
    # remove exclude node!
    # easiest way is to write a 'job_running' folder and tidy up on close... but this leads to own issues...
    # TODO: expose a function like 'compile kilosort mex files..."
    # questions 1) where to put code that is run on stitch
    # questions 2) worth making a spikewrap module?


def test_kilosort4_singularity():
    session = sw.Session(
        subject_path=DATA_SUB_PATH,
        session_name="ses-001",
        file_format="spikeglx",
    )

    # TODO: document well the class lifespan
    session.preprocess(
        configs="neuropixels+mountainsort5",
        # TODO: neuropixels+kilsort... allow possible ones, then choose sorter....
        per_shank=True,
        concat_runs=True,
    )

    config_dict = {"mountainsort5": {}}

    gpu_arguments = sw.default_slurm_options("gpu")

    gpu_arguments["mem_gb"] = 60
    gpu_arguments["env_name"] = "dammy-test"
    gpu_arguments["exclude"] = None

    session.sort(
        config_dict,
        "singularity",
        slurm=False,
    )


# TODO: test docker! maybe can do on CI?

# test_kilosort4_local()
# test_kilosort2_5_path()
# test_kilosort2_5_nomex()
test_kilosort4_singularity()
