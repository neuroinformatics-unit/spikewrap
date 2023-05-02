from pathlib import Path

from swc_ephys.pipeline.full_pipeline import run_full_pipeline

# base_path = Path(r"/home/joe/data")  # TODO: ~ syntax not working on linux
# sub_name = "1110925"
# run_names = "1110925_test_shank1_cut"

base_path = Path(
    r"/ceph/neuroinformatics/neuroinformatics/scratch/steve_multi_run/1119617/first_attempt"
)  # TODO: ~ syntax not working on linux
sub_name = "1119617"
run_names = "all"  # "1119617_posttest1_shank12_cut" #   "all" # ["", ""] # "all"

config_name = "test"  # or custom config file path
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
        slurm_batch=True,
    )
