from spikewrap.pipeline.load_data import load_spikeglx_data
from spikewrap.pipeline.preprocess import preprocess
from spikewrap.pipeline.visualise import visualise

base_path = r"X:\neuroinformatics\scratch\jziminski\ephys\test_data\steve_multi_run\1119617\time-short"
sub_name = "1119617"
run_names = "1119617_LSE1_shank12"

data = load_spikeglx_data(base_path, sub_name, run_names)

data = preprocess(data, pp_steps="default")

visualise(
    data,
    steps=["all"],
    mode="map",
    as_subplot=True,
    show_channel_ids=True,
    time_range=(0, 1),
    run_number=1,
)
