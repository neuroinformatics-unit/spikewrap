from pathlib import Path

from spikewrap.pipeline.load_data import load_data
from spikewrap.pipeline.preprocess import fill_all_runs_with_preprocessed_recording
from spikewrap.pipeline.visualise import visualise

base_path = Path(
    r"X:\neuroinformatics\scratch\jziminski\ephys\test_data\steve_multi_run\1119617\time-long_origdata"
)
sub_name = "1119617"
sessions_and_runs = {
    "ses-001": ["1119617_LSE1_shank12_g0"],
}

loaded_data = load_data(base_path, sub_name, sessions_and_runs, "spikeglx")

fill_all_runs_with_preprocessed_recording(loaded_data, pp_steps="default")

visualise(
    loaded_data,
    sessions_and_runs,
    steps=["all"],
    mode="map",
    as_subplot=False,
    show_channel_ids=True,
    time_range=(0, 1),
)
