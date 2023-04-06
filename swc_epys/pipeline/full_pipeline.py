"""
"""
from configs.configs import get_configs
from preprocess import preprocess
from quality import quality_check
from sort import run_sorting


def run_full_pipeline(
    base_path, sub_name, run_name, preprocessing_settings="test", sorter="kilosort2_5"
):
    """
    Must be run in main() as uses multiprocessing
    """
    pp_steps = get_configs(preprocessing_settings)

    # Get the recording object. This is lazy - no preprocessing
    # done yet
    data = preprocess(
        base_path=base_path, sub_name=sub_name, run_name=run_name, pp_steps=pp_steps
    )

    # Run sorting. This will save the final preprocessing step
    # recording to disk prior to sorting.
    run_sorting(data, sorter)

    # will save spikeinterface 'waveforms' output (TODO: currently, this is large)
    # to the sorter output dir. Quality checks are run and .csv of checks
    # output in the sorter folder as quality_metrics.csv
    quality_check(data.preprocessed_output_path, sorter)
