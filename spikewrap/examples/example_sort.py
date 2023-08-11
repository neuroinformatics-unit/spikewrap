from pathlib import Path

from spikewrap.pipeline.sort import run_sorting

base_path = Path(
    # r"C:\data\ephys\test_data\steve_multi_run\1119617\time-short"
    r"/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/test_data/steve_multi_run/1119617/time-short"
)
sub_name = "1119617"
run_names = [
    "1119617_LSE1_shank12_g0",
    "1119617_posttest1_shank12_g0",
    "1119617_pretest1_shank12_g0",
]


if __name__ == "__main__":
    # sorting uses multiprocessing so must be in __main__
    run_sorting(
        base_path,
        sub_name,
        run_names,
        sorter="mountainsort5",
        concat_for_sorting=True,
        #        sorter_options={"kilosort2_5": {"car": False}},
        existing_sorting_output="fail_if_exists",
        slurm_batch=False,
    )
