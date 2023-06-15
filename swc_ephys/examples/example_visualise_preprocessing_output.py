from pathlib import Path

from swc_ephys.pipeline.visualise import visualise
from swc_ephys.utils.utils import load_data_for_sorting

preprocessing_path = r"/home/joe/git-repos/swc_ephys/tests/data/steve_multi_run/derivatives/1119617/1119617_LSE1_shank12_cut_posttest1_pretest1/preprocessed"

sorting_data = load_data_for_sorting(
    Path(preprocessing_path),
)
visualise(sorting_data, time_range=(1, 2))
