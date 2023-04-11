"""
# this is actually very inefficient because
# for each chain it needs to pp all the way up (e.g. (0), (0-1), (0-1-2), (0-1-2-3))

# 1) for now assume spikeglx data
# 2) assume all gate, trigger, probe number are zero for now.
# Need to handle gate,trigger explicitly checking SI due to concatenation requirements
# probe number only requires iterating across user-passed probe numbers

# good Q should BD detection be before or after pp?

preprocess class
# note all LAZY

TODO: currently only supports one subject. Easy to add more, accept list
of sub names or search string. then add iterator over saving the data as so.

handle all file searching operations
TODO: fixed gate = 0
 # TODO: need to handle raw_data as top level path

 # good Q should bad channel detection be before or after pp?

     # TODO: I am 100% sure
# KS is running with its own PP after this PP..
# https://github.com/SpikeInterface/spikeinterface/issues/1018#issuecomment-1498743169

# if data, we need to pass the last recording in the preprocessing chain
# to run_sorter. First, we save in SI format (otherwise, run_sorter saves
# as less accessible binary with no metadata I can see). Then
# run sorting (SI SHOULD TODO) will know the fp for the saved recording
# already( TODO>!>!>)., Otherwise, if a str is passed, used the
# previously saved recording.

# TODO: rework file output
# have an option to save intermediate data, or can delete and just run full chain

# PP settings: can be None, set some defaults or always Force?

    # sorting uses multiprocessing and so MUST
# be run in __main__

# TODO: this is probably doing crazy stuff with kilosorts pp??? need to check carefuly
# the options KS is run with, and provide method to override ks settings

https://spikeinterface.readthedocs.io/en/latest/modules/qualitymetrics.html for
details on methods

TODO: almost certainly want this sparse, this is huge (12GB for 10GB data).
https://spikeinterface.readthedocs.io/en/latest/modules_gallery/core/plot_4_waveform_extractor.html

sorting_without_excess_spikes = curation.remove_excess_spikes(sorting, recording)
# TODO: this is required, what exactly is it doing?

 # TODO: handle g0 calls internally when gates / triggers method decided.

f"The following channels were detected as dead / noise: {bad_channels[0]}\n"
f"TODO: DO SOMETHING BETTER WITH THIS INFORMATION. SAVE IT SOMEHWERE\n"
f"You may like to automatically remove bad channels "
f"by setting XXX as a preprocessing option\n"
f"TODO: check how this is handled in SI"
)

what is remove exess spikes doing : sorting_without_excess_spikes =
    curation.remove_excess_spikes(sorting, recording)
example how to handle output when chaing options

for testing, use annotations
"""
from pathlib import Path

from swc_ephys.pipeline.full_pipeline import run_full_pipeline

base_path = Path(r"/ceph/neuroinformatics/neuroinformatics/scratch/ece_ephys_learning")
sub_name = "1110925"
run_name = "1110925_test_shank1"

pp_config = "test"  # or custom config file path
sorter = "kilosort2_5"

if __name__ == "__main__":
    run_full_pipeline(
        base_path, sub_name, run_name, pp_config, sorter, use_existing=True
    )
