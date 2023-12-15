import time
from pathlib import Path

from spikewrap.pipeline.full_pipeline import run_full_pipeline

base_path = Path(r"C:\Users\Joe\work\git-repos\spikewrap\tests\data\small_toy_data")

sub_name = "sub-001_type-test"
sessions_and_runs = {
    "ses-001": ["ses-001_run-001", "ses-001_run-002"],
    "ses-002": ["ses-002_run-001", "ses-002_run-002"],
    "ses-003": ["ses-003_run-001", "ses-003_run-002"],
}

config_name = "test_default"
sorter = "mountainsort5"  #  "kilosort2_5"  # "spykingcircus" # mountainsort5

if __name__ == "__main__":
    t = time.time()

    run_full_pipeline(
        base_path,
        sub_name,
        sessions_and_runs,
        "spikeinterface",
        config_name,
        sorter,
        concat_sessions_for_sorting=True,  # TODO: validate this at the start, in `run_full_pipeline`
        concat_runs_for_sorting=True,
        #        existing_preprocessed_data="skip_if_exists",  # this is kind of confusing...
        #       existing_sorting_output="overwrite",
        #      overwrite_postprocessing=True,
        #     slurm_batch=False,
    )

    print(f"TOOK {time.time() - t}")
