from pathlib import Path

from spikewrap.pipeline.load_data import load_data
from spikewrap.pipeline.preprocess import run_preprocess

base_path = Path(
    r"C:\data\ephys\test_data\steve_multi_run\1119617\time-miniscule-multises"
)

sub_name = "sub-1119617"
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

loaded_data = load_data(base_path, sub_name, sessions_and_runs, data_format="spikeglx")

run_preprocess(loaded_data, pp_steps="default", save_to_file="fail_if_exists", log=True)
