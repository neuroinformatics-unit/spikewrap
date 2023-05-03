import numpy as np

from swc_ephys.pipeline.load_data import load_spikeglx_data
from swc_ephys.pipeline.preprocess import preprocess
from swc_ephys.pipeline.visualise import visualise

base_path = r"N:\neuroinformatics\scratch\jziminski\ephys\test_data\steve_single_run"
sub_name = "1110925"
run_names = "1110925_test_shank1"

data = load_spikeglx_data(base_path, sub_name, run_names)

data = preprocess(data)

visualise(
    data,
    steps=["all"],
    mode="map",
    as_subplot=False,
    channel_idx_to_show=np.arange(10, 50),
    show_channel_ids=True,
    time_range=(0, 1),
    run_number=1,
)
