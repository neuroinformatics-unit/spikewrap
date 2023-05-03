from pathlib import Path

from swc_ephys.pipeline.full_pipeline import run_full_pipeline

base_path = Path(
    r"/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/test_data/steve_multi_run/1119617"
    r"/time-short_samenaming"
)
sub_name = "cut_same_name"  # "cut_same_name"
run_names = "all"

config_name = "test"
sorter = "kilosort2_5"

if __name__ == "__main__":
    run_full_pipeline(
        base_path,
        sub_name,
        run_names,
        config_name,
        sorter,
        use_existing_preprocessed_file=True,
        overwrite_existing_sorter_output=True,
        slurm_batch=False,
    )
