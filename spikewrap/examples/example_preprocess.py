from pathlib import Path

from spikewrap.pipeline.load_data import load_data
from spikewrap.pipeline.preprocess import PreprocessPipeline

base_path = Path(
    "/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/code/spikewrap/tests/data/small_toy_data"
    # r"C:\fMRIData\git-repo\spikewrap\tests\data\small_toy_data"
    # r"/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/test_data/steve_multi_run/1119617/time-short-multises"
    # r"C:\data\ephys\test_data\steve_multi_run\1119617\time-miniscule-multises"
)

sub_name = "sub-001_type-test"
# sub_name = "sub-1119617"

sessions_and_runs = {
    "ses-001": ["all"],
    "ses-002": ["all"],
}

if False:
    sessions_and_runs = {
        "ses-001": [
            "run-001_1119617_LSE1_shank12_g0",
            "run-002_made_up_g0",
        ],
        "ses-002": [
            "run-001_1119617_pretest1_shank12_g0",
        ],
        "ses-003": [
            "run-002_1119617_pretest1_shank12_g0",
        ],
    }

loaded_data = load_data(
    base_path, sub_name, sessions_and_runs, data_format="spikeinterface"
)

preprocess_pipeline = PreprocessPipeline(
    loaded_data,
    pp_steps="default",
    handle_existing_data="overwrite",
    preprocess_by_group=True,
    log=True,
)
preprocess_pipeline.run(slurm_batch=True)
