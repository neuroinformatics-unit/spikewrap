"""
# this is actually very inefficient because
# for each chain it needs to pp all the way up (e.g. (0), (0-1), (0-1-2), (0-1-2-3))
"""
from preprocess import preprocess
from visualise import visualise
import numpy as np

base_path = r"/ceph/neuroinformatics/neuroinformatics/scratch/ece_ephys_learning"
sub_name = "1110925"
run_name = "1110925_test_shank1"

data = preprocess(base_path=base_path,
                  sub_name=sub_name,
                  run_name=run_name)


visualise(data,
          steps=["0"],
          mode="map",
          as_subplot=True,
          channels_to_show=None, # np.arange(10, 50),
          show_channel_ids=False,
          time_range=None)

