from spikewrap.pipeline.load_data import load_data
from spikewrap.pipeline.preprocess import preprocess
from spikewrap.pipeline.visualise import visualise

base_path = r"C:\data\ephys\test_data\steve_multi_run\1119617\time-short"
sub_name = "1119617"
run_names = [
    "1119617_LSE1_shank12_g0",
    #  "1119617_posttest1_shank12_g0",
    #  "1119617_pretest1_shank12_g0",
]


data = load_data(base_path, sub_name, run_names, "spikeglx")

for run_name in run_names:
    preprocess_data = preprocess(data, run_name, pp_steps="default")

    visualise(
        preprocess_data,
        run_name,
        steps=["all"],
        mode="map",
        as_subplot=True,
        show_channel_ids=False,
        time_range=(0, 1),
    )
