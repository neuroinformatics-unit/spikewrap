from pathlib import Path

from swc_ephys.pipeline.full_pipeline import run_full_pipeline

base_path = Path(r"/home/joe/data/steve_multi_run")  # TODO: ~ syntax not working on linux
sub_name = "1119617"
run_name = "all"

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
