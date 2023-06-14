from swc_ephys.pipeline.visualise import visualise_preprocessing_output, visualise
from swc_ephys.utils.utils import load_data_for_sorting
from pathlib import Path

preprocessing_path = (
    r"X:\neuroinformatics\scratch\jziminski\ephys\test_data\steve_multi_run\1119617\time-short_samenaming\derivatives\cut_same_name\1119617_test_units_explore_shank1_cut_shank2_shank3\preprocessed"  # TODO: this is a stupid pattern now base_path can be input
    # this strange behaviour when the saved path is different must be very clear.
)

sorting_data = load_data_for_sorting(Path(preprocessing_path),
                                     base_path=r"X:\neuroinformatics\scratch\jziminski\ephys\test_data\steve_multi_run\1119617\time-short_samenaming")
visualise(sorting_data, time_range=(1, 2))
