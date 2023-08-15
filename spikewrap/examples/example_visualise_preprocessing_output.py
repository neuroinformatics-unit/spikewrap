from pathlib import Path

from spikewrap.pipeline.visualise import visualise_preprocessed

# WARNING ------------------- THIS DOES NOT CURRENTLY WORK ----------------------------#
# WARNING ------------------- THIS DOES NOT CURRENTLY WORK ----------------------------#
# WARNING ------------------- THIS DOES NOT CURRENTLY WORK ----------------------------#

# TODO: move this into a convenience wrapper.
# TODO: need to completely rework this in lgiht of recent refactorings.
#
base_path = Path(r"C:\data\ephys\test_data\steve_multi_run\1119617\time-short-multises")
sub_name = "sub-1119617"
sessions_and_runs = {
    "ses-001": ["run-001_1119617_LSE1_shank12_g0", "run-002_made_up_g0"],
    "ses-002": [
        "run-001_1119617_pretest1_shank12_g0",
        "run-002_1119617_LSE1_shank12_g0",
    ],
    "ses-003": [
        "run-001_1119617_posttest1_shank12_g0",
        "run-002_1119617_pretest1_shank12_g0",
    ],
}

# TODO: the problem is visualise has an extra dict layer ["0-raw"] while
# preprocessed data does not.
visualise_preprocessed(
    base_path,
    sub_name,
    sessions_and_runs,
    concatenate_sessions=False,
    concatenate_runs=False,
    show_channel_ids=False,
    time_range=(0, 1),
)
