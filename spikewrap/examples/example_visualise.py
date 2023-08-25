from pathlib import Path

from spikewrap.pipeline.load_data import load_data
from spikewrap.pipeline.preprocess import preprocess
from spikewrap.pipeline.visualise import visualise

base_path = Path(
    r"X:\neuroinformatics\scratch\jziminski\ephys\test_data\steve_multi_run\1119617\time-long_origdata"
)
sub_name = "1119617"
sessions_and_runs = {
    "ses-001": ["1119617_LSE1_shank12_g0"],
}

data = load_data(base_path, sub_name, sessions_and_runs, "spikeglx")

for ses_name, run_name in data.preprocessing_sessions_and_runs():
    preprocess(data, ses_name, run_name, pp_steps="default")

visualise(
    data,
    sessions_and_runs,
    steps=["2"],
    mode="map",
    as_subplot=False,
    show_channel_ids=True,
    time_range=(0, 1),
)
