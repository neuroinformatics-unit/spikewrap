from pathlib import Path

from spikewrap.pipeline.full_pipeline import run_full_pipeline

base_path = Path(
    # r"C:\data\ephys\test_data\steve_multi_run\1119617\time-short"
    "/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/test_data/steve_multi_run/1119617/time-short"
)

sub_name = "1119617"
run_names = [
    "1119617_LSE1_shank12_g0",
    "1119617_posttest1_shank12_g0",
    "1119617_pretest1_shank12_g0",
]

config_name = "default"
sorter = "kilosort2_5"  #  "kilosort2_5"  # "spykingcircus" # mountainsort5

if __name__ == "__main__":
    run_full_pipeline(
        base_path,
        sub_name,
        run_names,
        config_name,
        sorter,
        concat_for_sorting=True,
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
