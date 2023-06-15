import numpy as np

from swc_ephys.pipeline.load_data import load_spikeglx_data
from swc_ephys.pipeline.preprocess import preprocess
from swc_ephys.pipeline.visualise import visualise

base_path = r"X:\neuroinformatics\scratch\jziminski\ephys\test_data\steve_multi_run\1119617\time-short"
sub_name = "1119617"
run_names = "1119617_LSE1_shank12"

data = load_spikeglx_data(base_path, sub_name, run_names)

data = preprocess(data)

visualise(
    data,
    steps=["all"],
    mode="map",
    as_subplot=True,
    channel_idx_to_show=np.arange(10, 50),
    show_channel_ids=True,
    time_range=(0, 1),
    run_number=1,
)
