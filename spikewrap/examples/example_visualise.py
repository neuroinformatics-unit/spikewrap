from spikewrap.pipeline.preprocess import preprocess
from spikewrap.pipeline.visualise import visualise
from spikewrap.pipline.load_data import load_data

base_path = r"X:\neuroinformatics\scratch\jziminski\ephys\test_data\steve_multi_run\1119617\time-short"
sub_name = "1119617"
run_names = "1119617_LSE1_shank12"

data = load_data.load_data(base_path, sub_name, run_names, "spikeglx")

for run_name in run_names:
    preprocess_data = preprocess(
        data, run_name, pp_steps="default"
    )  # TODO: need to fix now!

visualise(
    preprocess_data,
    steps=["all"],
    mode="map",
    as_subplot=True,
    show_channel_ids=True,
    time_range=(0, 1),
    run_number=1,
)
