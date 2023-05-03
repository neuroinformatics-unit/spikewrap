"""
# TODO: this is actually very inefficient because
# for each chain it needs to pp all the way up (e.g. (0), (0-1), (0-1-2), (0-1-2-3))
"""
from swc_ephys.pipeline.load_data import load_spikeglx_data
from swc_ephys.pipeline.preprocess import preprocess
from swc_ephys.pipeline.visualise import visualise

base_path = r"N:\neuroinformatics\scratch\jziminski\ephys\test_data\steve_single_run"
# r"/ceph/neuroinformatics/scratch/jziminski/ephys/test_data/steve_single_run"
sub_name = "1110925"
run_names = "1110925_test_shank1_g0"  # ["1119617_LSE1_shank12_cut", "
# 1119617_pretest1_shank12_cut"]

data = load_spikeglx_data(base_path, sub_name, run_names)

data = preprocess(data)

visualise(
    data,
    steps=["all"],
    mode="map",
    as_subplot=True,
    channel_idx_to_show=None,  # np.arange(10, 50),
    show_channel_ids=False,
    time_range=(
        0,
        1,
    ),  # TODO: raise sensible error if this is longer than the recording time
    run_number=2,
)
