from pathlib import Path

from swc_ephys.pipeline.full_pipeline import run_full_pipeline

base_path = Path(r"/ceph/neuroinformatics/neuroinformatics/scratch/ece_ephys_learning")
sub_name = "1110925"
run_name = "1110925_test_shank1_cut"

config_name = "test"  # or custom config file path
sorter = "kilosort2_5"

if __name__ == "__main__":
    run_full_pipeline(
        base_path,
        sub_name,
        run_name,
        config_name,
        sorter,
        use_existing_preprocessed_file=True,
    )
