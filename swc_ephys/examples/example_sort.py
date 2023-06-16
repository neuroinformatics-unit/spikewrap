from pathlib import Path

from swc_ephys.pipeline.load_data import load_spikeglx_data
from swc_ephys.pipeline.preprocess import preprocess
from swc_ephys.pipeline.sort import run_sorting

base_path = Path(
    "/ceph/neuroinformatics/neuroinformatics/scratch/steve_multi_run/1119617/first_attempt/time-short_samenaming"
)
sub_name = "cut_same_name"
run_names = "all"

preprocess_data = load_spikeglx_data(base_path, sub_name, run_names)

preprocess_data = preprocess(preprocess_data)

if __name__ == "__main__":
    # sorting uses multiprocessing so must be in __main__
    run_sorting(
        preprocess_data.preprocessed_data_path,
        sorter="kilosort2_5",
        sorter_options={"kilosort2_5": {"car": False}},
        overwrite_existing_sorter_output=True,
        slurm_batch=False,
    )
