import time
from pathlib import Path

from spikewrap.pipeline.load_data import load_data
from spikewrap.pipeline.preprocess import preprocess

base_path = Path(
    "/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/test_data/steve_multi_run/1119617/time-long_origdata"
)

sub_name = "1119617"
sessions_and_runs = {
    #    "ses-001": [
    #        "1119617_LSE1_shank12_g0",
    #    ],
    "ses-002": [
        "1119617_pretest1_shank12_g0",
    ],
    #    "ses-003": [
    #        "1119617_posttest1_shank12_g0",
    #    ],
}

loaded_data = load_data(base_path, sub_name, sessions_and_runs, data_format="spikeglx")

for ses_name in sessions_and_runs.keys():
    for run_name in sessions_and_runs[ses_name]:
        t = time.time()

        preprocess_data = preprocess(
            loaded_data, ses_name, run_name, pp_steps="default"
        )
        preprocess_data.save_preprocessed_data(ses_name, run_name, overwrite=True)

        print(f"ses: {ses_name}, run: {run_name} took {time.time() - t}")
