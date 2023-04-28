from pathlib import Path

from swc_ephys.pipeline.load_data import load_spikeglx_data
from swc_ephys.pipeline.preprocess import preprocess
from swc_ephys.pipeline.sort import run_sorting

base_path = Path(
    "/home/joe/data"
)  # Path(r"/ceph/neuroinformatics/neuroinformatics/scratch/ece_ephys_learning")
sub_name = "1110925"
run_names = "1110925_test_shank1_cut"

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
    )
