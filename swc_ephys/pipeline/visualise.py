from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Tuple, Union

if TYPE_CHECKING:
    import matplotlib
    from numpy.typing import NDArray
    from spikeinterface.core import BaseRecording

from ..data_classes.preprocessing import PreprocessingData
from ..data_classes.sorting import SortingData

import inspect
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import spikeinterface.widgets as sw

from ..utils import utils


def visualise(
    data: Union[PreprocessingData, SortingData],
    steps: Union[List[str], str] = "all",
    mode: str = "auto",
    as_subplot: bool = False,
    channel_idx_to_show: Union[List, Tuple, NDArray, None] = None,
    time_range: Optional[Tuple] = None,
    show_channel_ids: bool = False,
    run_number: int = 1,
) -> None:
    """
    Plot the data at various preprocessing steps, useful for quality-checking.
    Takes the pipeline.data_class.PreprocessingData object (output from pipeline.preprocess).
    Channels are displayed ordered by depth. Note preprocessing is lazy, and only the
    section if data displayed will be preprocessed.

    If multiple preprocessing steps are shown, they will be placed in subplots
    on a single plot if as_subplots is True, otherwise in separate plots.

    data : swc_ephys PreprocessingData class containing the preprocessing output (a dict
           of keys indicating the preprocessing step and values are spikeinterface
           recording objects.

    steps : the preprocessing steps to show, specified as a number (e.g. "1"),
            or list of numbers ["1", "2", "3"] or "all" to show multiple steps.

    mode : "line" to show line plot, "map" to show as image, or "auto" to determine
            based on the number of displayed channels.

    as_subplot : if True, multiple preprocessing steps will be displayed as subplots
                 on the same plot. Otherwise, they will be plot as separate plots.

    channel_idx_to_show : index of channels to show (e.g. [0, 1, 2, 3...]). Note
                          that this is the channel index (not ordered by depth)

    time_range : time range of data to display in seconds e.g. (1, 5) will display the
                 range 1- 5 s.

    show_channel_ids : if True, channel IDS will be displayed on the plot.

    run_number : The run number to visualise (in the case of a concatenated recording.
                 Under the hood, each run maps to a SpikeInterface segment_index.
    """
    steps, as_subplot, channel_idx_to_show = process_input_arguments(
        data, steps, as_subplot, channel_idx_to_show
    )

    total_used_shanks = utils.get_probe_group_num(data)

    for shank_idx in range(total_used_shanks):
        if as_subplot:
            fig, ax, num_rows, num_cols = generate_subplot(steps)

        for idx, step in enumerate(steps):
            recording, full_key = utils.get_dict_value_from_step_num(data, str(step))

            validate_options_against_recording(recording, data, time_range, run_number)

            recordings = recording.split_by(property="group")
            recording_to_plot = recordings[shank_idx]

            run_name = get_run_name(data, run_number)

            plot_title = utils.make_preprocessing_plot_title(
                run_name,
                full_key,
                shank_idx,
                recording_to_plot,
                total_used_shanks,
            )

            current_ax = (
                None if not as_subplot else get_subplot_ax(idx, ax, num_rows, num_cols)
            )

            channel_ids_to_show = get_channel_ids_to_show(
                recording_to_plot, channel_idx_to_show
            )

            sw.plot_timeseries(
                recording_to_plot,
                channel_ids=channel_ids_to_show,
                order_channel_by_depth=False,
                time_range=time_range,
                return_scaled=True,
                show_channel_ids=show_channel_ids,
                mode=mode,
                ax=current_ax,
                segment_index=run_number - 1,
            )

            if current_ax is None:
                plt.title(plot_title)
                plt.show()
            else:
                current_ax.set_title(plot_title)

        if as_subplot:
            plt.show()


def get_channel_ids_to_show(
    recording_to_plot: BaseRecording, channel_idx_to_show: int
) -> List[str]:
    """
    Channel ids are returned in default order (e.g. 0, 1, 2...)
    not ordered by depth.
    """
    if channel_idx_to_show is None:
        channel_ids_to_show = None
    else:
        channel_ids = recording_to_plot.get_channel_ids()
        channel_ids_to_show = channel_ids[channel_idx_to_show]

    return channel_ids_to_show


def generate_subplot(
    steps: Union[List[str], str]
) -> Tuple[matplotlib.figure.Figure, NDArray, int, int,]:
    num_cols = 2
    num_rows = np.ceil(len(steps) / num_cols).astype(int)
    fig, ax = plt.subplots(num_rows, num_cols)
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    return fig, ax, num_rows, num_cols


def get_subplot_ax(idx, ax, num_rows, num_cols) -> matplotlib.axes._axes.Axes:
    idx_unraveled = np.unravel_index(idx, shape=(num_rows, num_cols))
    current_ax = ax[idx_unraveled]
    return current_ax


def process_input_arguments(
    data: PreprocessingData,
    steps: Union[List[str], str],
    as_subplot: bool,
    channel_idx_to_show: Union[List, Tuple, NDArray, None],
) -> Tuple[Union[List[str], str], bool, int]:
    """ """
    if not isinstance(steps, List):
        steps = [steps]

    if "all" in steps:
        assert len(steps) == 1, "if using 'all' only put one step input"
        steps = utils.get_keys_first_char(data)  # type: ignore

    assert len(steps) <= len(data), (
        "The number of steps must be less or equal to the "
        "number of steps in the recording"
    )

    if len(steps) == 1 and as_subplot:
        as_subplot = False

    if channel_idx_to_show is not None and not isinstance(
        channel_idx_to_show, np.ndarray
    ):
        channel_idx_to_show = np.array(channel_idx_to_show, dtype=np.int32)

    return steps, as_subplot, channel_idx_to_show


def validate_options_against_recording(
    recording: BaseRecording, data: PreprocessingData, time_range: Optional[Tuple], run_number: int
) -> None:
    """
    TODO: can't find a better way to get final timepoint, but must be
    somewhere, this is wasteful.
    """
    if isinstance(data, PreprocessingData):
        num_runs = len(data.all_run_names)
        assert run_number <= num_runs, (
            "The run_number must be less than or equal to the " "number of runs specified."
        )
    if time_range is not None:
        assert (
            time_range[1] <= recording.get_times(segment_index=run_number - 1)[-1]
        ), "The time range specified is longer than the maximum time of the recording."


def get_run_name(data, run_number):
    if isinstance(data, PreprocessingData):
        run_name = data.all_run_names[run_number - 1]
    elif isinstance(data, SortingData):
        run_name = data.pp_run_name
    return run_name