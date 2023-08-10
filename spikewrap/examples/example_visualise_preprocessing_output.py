from pathlib import Path

from spikewrap.data_classes.sorting import SortingData
from spikewrap.pipeline.visualise import visualise

# WARNING ------------------- THIS DOES NOT CURRENTLY WORK ----------------------------#

# TODO: move this into a convenience wrapper.
# TODO: need to completely rework this in lgiht of recent refactorings.
#
base_path = Path(r"C:\data\ephys\test_data\steve_multi_run\1119617\time-short")
sub_name = "1119617"
run_names = [
    "1119617_LSE1_shank12_g0",
    #    "1119617_posttest1_shank12_g0",
    #    "1119617_pretest1_shank12_g0",
]

sorting_data = SortingData(
    base_path,
    sub_name,
    run_names,
    sorter="kilsort2_5",  # This does nothing here
    concat_for_sorting=False,  # TODO: this is a bad variable name here.
)

for run_name in run_names:
    visualise(sorting_data, run_name, time_range=(1, 2))
