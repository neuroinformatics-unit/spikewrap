from pathlib import Path
from typing import Union

from ..configs.configs import get_configs
from .load_data import load_spikeglx_data
from .preprocess import preprocess
from .quality import quality_check
from .sort import run_sorting

# make note that pp is all per-segment (make an option for this later)
# now we concatenate files together at the segment level. STILL NEED TO CONCAT SEGMETNS PRIOR TO SORTING!?
# make it super clear g0 not included on run name,... in antipatciaton to handle other gate /trigger. Up until then coould accept.
# TODO: currently only spikeglx supported
# should the derivatives output have the gate idx? thinking forward in case gates will be supported


def run_full_pipeline(
    base_path: Union[Path, str],
    sub_name: str,
    run_names: str,
    config_name: str = "test",
    sorter: str = "kilosort2_5",
    use_existing_preprocessed_file: bool = False,
    overwrite_existing_sorter_output: bool = False,
    verbose: bool = True,
):
    """
    Run preprocessing, sorting and quality checks on SpikeGLX data.
    see README.md for detailed information on use.

    This function must be run in main as uses multiprocessing e.g.
    if __name__ == "__main__":
        run_full_pipieline(args...)

    Parameters
    __________

    base_path : path where the rawdata folder containing subjects.

    sub_name : subject to preprocess. The subject top level dir should reside in
               base_path/rawdata/

    run_names : the spikeglx run name (i.e. not including the gate index). This can
                also be a list of run names, or "all", in which case all runs in that
                folder will be concatenated and sorted together. Preprocessing will still
                occur per-run. Runs will always be concatenated in date order. TODO: offer key to disable this.

    configs_name : the name of the configuration to use. Note this must be the name
                   of .yaml file (not including the extension) stored in
                   swc_ephys/configs.

    sorter : name of the sorter to use e.g. "kilosort2_5".

    use_existing_preprocessed_file : if this function has been run previoulsly
                                     and a saved preproccessed binary already
                                     exists in the 'preprocessed' folder for this
                                     subject, it will be used. If False and this folder
                                     exists, an error will be raised.
    """
    pp_steps, sorter_options = get_configs(config_name)

    # Load the data from file (lazy)
    data = load_spikeglx_data(base_path, sub_name, run_names)

    # This is lazy - no preprocessing done yet
    data = preprocess(data, pp_steps, verbose)

    # Run sorting. This will save the final preprocessing step
    # recording to disk prior to sorting.
    run_sorting(
        data,
        sorter,
        sorter_options,
        use_existing_preprocessed_file,
        overwrite_existing_sorter_output,
        verbose,
    )

    # Save spikeinterface 'waveforms' output (TODO: currently, this is large)
    # to the sorter output dir. Quality checks are run and .csv of checks
    # output in the sorter folder as quality_metrics.csv
    quality_check(data.preprocessed_output_path, sorter, verbose)
