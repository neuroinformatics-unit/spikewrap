import time
from pathlib import Path

from spikewrap.pipeline.full_pipeline import run_full_pipeline_wrapper

base_path = Path(
    "/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/code/spikewrap/tests/data/steve_multi_run/time-short-multises"
    # "/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/test_data/steve_multi_run/1119617/time-short-multises"
    # r"C:\data\ephys\test_data\steve_multi_run\1119617\time-miniscule-mutlises"
    # r"C:\data\ephys\test_data\steve_multi_run\1119617\time-short-multises"
    # "/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/test_data/steve_multi_run/1119617/time-short"
)

sub_name = "sub-1119617"
sessions_and_runs = {
    "ses-001": ["run-001_1119617_LSE1_shank12_g0", "run-002_made_up_g0"],
    "ses-002": [
        "run-002_1119617_LSE1_shank12_g0",
        "run-001_1119617_pretest1_shank12_g0",
    ],
    "ses-003": [
        "run-001_1119617_posttest1_shank12_g0",
        "run-002_1119617_pretest1_shank12_g0",
    ],
}

config_name = "test_default"
sorter = "mountainsort5"  #  "kilosort2_5"  # "spykingcircus" # mountainsort5

if __name__ == "__main__":
    t = time.time()

    run_full_pipeline_wrapper(
        base_path,
        sub_name,
        sessions_and_runs,
        config_name,
        sorter,
        concat_sessions_for_sorting=True,  # TODO: validate this at the start, in `run_full_pipeline_wrapper`
        concat_runs_for_sorting=True,
        existing_preprocessed_data="skip_if_exists",  # this is kind of confusing...
        existing_sorting_output="skip_if_exists",
        overwrite_postprocessing=True,
        delete_intermediate_files=(),
        #        "recording.dat",
        #       "temp_wh.dat",
        #      "waveforms",
        # ),
        slurm_batch=True,
    )

    print(f"TOOK {time.time() - t}")
