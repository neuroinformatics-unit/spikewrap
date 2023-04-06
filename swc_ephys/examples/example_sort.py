"""
# this is actually very inefficient because
# for each chain it needs to pp all the way up (e.g. (0), (0-1), (0-1-2), (0-1-2-3))
"""
from pathlib import Path

from swc_ephys.pipeline.preprocess import preprocess
from swc_ephys.pipeline.sort import run_sorting

base_path = Path(r"/ceph/neuroinformatics/neuroinformatics/scratch/ece_ephys_learning")
sub_name = "1110925"
run_name = "1110925_test_shank1"

data = preprocess(base_path=base_path, sub_name=sub_name, run_name=run_name)

if __name__ == "__main__":
    # sorting uses multiprocessing so must be in __main__
    run_sorting(
        data, sorter="kilosort2_5", sorter_options={"kilosort2_5": {"car": False}}
    )  # TODO: this is stupid
