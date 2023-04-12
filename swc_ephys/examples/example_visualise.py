"""
# TODO: this is actually very inefficient because
# for each chain it needs to pp all the way up (e.g. (0), (0-1), (0-1-2), (0-1-2-3))
"""

from swc_ephys.pipeline.preprocess import preprocess
from swc_ephys.pipeline.visualise import visualise

base_path = r"C:\data\spike_interface"
sub_name = "1110925"
run_name = "1110925_test_shank1"

data = preprocess(base_path=base_path, sub_name=sub_name, run_name=run_name)

visualise(
    data,
    steps=["all"],
    mode="map",
    as_subplot=True,
    channel_idx_to_show=None,  # np.arange(10, 50),
    show_channel_ids=False,
    time_range=(200, 200.5),
)
