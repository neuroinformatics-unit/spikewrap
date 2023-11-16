from pathlib import Path

from spikewrap.pipeline.sort import run_sorting

base_path = Path(
    r"/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/test_data/steve_multi_run/1119617/time-short-multises"
)
sub_name = "sub-1119617"
sessions_and_runs = {
    "ses-001": ["run-001_1119617_LSE1_shank12_g0"],
}


if __name__ == "__main__":
    # sorting uses multiprocessing so must be in __main__
    run_sorting(
        base_path,
        sub_name,
        sessions_and_runs,
        existing_sorting_output="overwrite",
        sorter="mountainsort5",
        concatenate_runs=True,
        concatenate_sessions=False,
        slurm_batch=True,
    )
