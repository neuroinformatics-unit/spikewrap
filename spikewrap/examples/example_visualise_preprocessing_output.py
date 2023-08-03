from pathlib import Path

from swc_ephys.pipeline.load_data import load_data_for_sorting
from swc_ephys.pipeline.visualise import visualise

preprocessing_path = r"X:\neuroinformatics\scratch\jziminski\ephys\test_data\steve_multi_run\1119617\time-short\derivatives\1119617\1119617_LSE1_shank12_posttest1_pretest1\preprocessed"

sorting_data = load_data_for_sorting(
    Path(preprocessing_path),
)
visualise(sorting_data, time_range=(1, 2))
