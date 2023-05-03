from pathlib import Path

from swc_ephys.pipeline.load_data import load_spikeglx_data
from swc_ephys.pipeline.preprocess import preprocess
from swc_ephys.pipeline.sort import run_sorting

base_path = Path(
    "/ceph/neuroinformatics/neuroinformatics/scratch/steve_multi_run/1119617/first_attempt"
)
sub_name = "1119617"
run_names = "all"

data = load_spikeglx_data(base_path, sub_name, run_names)

data = preprocess(data)

if __name__ == "__main__":
    # sorting uses multiprocessing so must be in __main__
    run_sorting(
        data,
        sorter="kilosort2_5",
        sorter_options={"kilosort2_5": {"car": False}},
        use_existing_preprocessed_file=True,
        overwrite_existing_sorter_output=True,
        slurm_batch=True,
    )
