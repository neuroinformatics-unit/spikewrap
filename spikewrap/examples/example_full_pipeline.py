from pathlib import Path

from spikewrap.pipeline.full_pipeline import run_full_pipeline

base_path = Path(
    r"C:\data\ephys\test_data\steve_multi_run\1119617\time-short-multises"
    # "/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/test_data/steve_multi_run/1119617/time-short"
)

sub_name = "sub-1119617"
ses_names = ["ses-001", "ses-002", "ses-003"]
run_names = [
    "1119617_LSE1_shank12_g0",
    "1119617_posttest1_shank12_g0",
    "1119617_pretest1_shank12_g0",
]

sessions_and_runs = {
    "ses-001": ["run-001_1119617_LSE1_shank12_g0", "run-002_made_up_g0"],
    "ses-002": [
        "run-001_1119617_pretest1_shank12_g0",
        "run-002_1119617_LSE1_shank12_g0",
    ],
    "ses-003": [
        "run-001_1119617_posttest1_shank12_g0",
        "run-002_1119617_pretest1_shank12_g0",
    ],
}

config_name = "default"
sorter = "mountainsort5"  #  "kilosort2_5"  # "spykingcircus" # mountainsort5

if __name__ == "__main__":
    run_full_pipeline(
        base_path,
        sub_name,
        sessions_and_runs,
        config_name,
        sorter,
        concat_sessions_for_sorting=False,  # TODO: validate this at the start, in `run_full_pipeline`
        concat_runs_for_sorting=False,
        existing_preprocessed_data="load_if_exists",
        existing_sorting_output="load_if_exists",
        overwrite_postprocessing=True,
        delete_intermediate_files=(
            "recording.dat",
            "temp_wh.dat",
            "waveforms",
        ),
        slurm_batch=False,
    )
