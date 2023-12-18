import time
from pathlib import Path

from spikewrap.pipeline.full_pipeline import run_full_pipeline

base_path = Path(
    # r"/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/test_data/steve_multi_run/1119617/time-long_origdata"
    r"C:\fMRIData\git-repo\spikewrap\tests\data\small_toy_data",
)

sub_name = "sub-001_type-test"

sessions_and_runs = {
    "all": ["all"],
}

# sub_name = "1119617"
# sessions_and_runs = {
#     "ses-001": ["1119617_LSE1_shank12_g0"],
# }

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
        sort_by_group=True,
        save_preprocessing_chunk_size=30000,
        existing_preprocessed_data="overwrite",
        existing_sorting_output="overwrite",
        overwrite_postprocessing=True,
        concat_sessions_for_sorting=False,  # TODO: validate this at the start, in `run_full_pipeline`
        concat_runs_for_sorting=False,
    )

    print(f"TOOK {time.time() - t}")
