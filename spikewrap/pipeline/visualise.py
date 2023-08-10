from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import spikeinterface.widgets as sw

from ..data_classes.preprocessing import PreprocessingData
from ..data_classes.sorting import SortingData
from ..utils import utils

if TYPE_CHECKING:
    import matplotlib
    from numpy.typing import NDArray
    from spikeinterface.core import BaseRecording


def visualise(
    data: Union[PreprocessingData, SortingData],
    run_name: str,
    steps: Union[List[str], str] = "all",
    mode: str = "auto",
    as_subplot: bool = False,
    time_range: Optional[Tuple] = None,
    show_channel_ids: bool = False,
) -> None:
    """
    Plot the data at various preprocessing steps, useful for quality-checking.
    Takes the pipeline.data_class.PreprocessingData object
    (output from pipeline.preprocess).

    Channels are displayed ordered by depth. Note preprocessing is lazy, and only the
    section if data displayed will be preprocessed.

    If multiple preprocessing steps are shown, they will be placed in subplots
    on a single plot if as_subplots is True, otherwise in separate plots.

    data : spikewrap PreprocessingData class containing the preprocessing output (a dict
           of keys indicating the preprocessing step and values are spikeinterface
           recording objects.

    steps : the preprocessing steps to show, specified as a number (e.g. "1"),
            or list of numbers ["1", "2", "3"] or "all" to show multiple steps.

    mode : "line" to show line plot, "map" to show as image, or "auto" to determine
            based on the number of displayed channels.

    as_subplot : if True, multiple preprocessing steps will be displayed as subplots
                 on the same plot. Otherwise, they will be plot as separate plots.

    time_range : time range of data to display in seconds e.g. (1, 5) will display the
                 range 1- 5 s.

    show_channel_ids : if True, channel IDS will be displayed on the plot.

    run_number : The run number to visualise (in the case of a concatenated recording.
                 Under the hood, each run maps to a SpikeInterface segment_index.
    """
    steps, as_subplot = process_input_arguments(data, run_name, steps, as_subplot)

    first_key = list(data[run_name].keys())[-1]
    total_used_shanks = np.unique(
        data[run_name][first_key].get_property("group")
    ).size  # TODO

    for shank_idx in range(total_used_shanks):
        if as_subplot:
            fig, ax, num_rows, num_cols = generate_subplot(steps)

        for idx, step in enumerate(steps):
            recording, full_key = utils.get_dict_value_from_step_num(
                data[run_name], str(step)
            )

            validate_options_against_recording(recording, data, run_name, time_range)

            recordings = recording.split_by(property="group")
            recording_to_plot = recordings[shank_idx]

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

            sw.plot_timeseries(
                recording_to_plot,
                order_channel_by_depth=False,
                time_range=time_range,
                return_scaled=True,
                show_channel_ids=show_channel_ids,
                mode=mode,
                ax=current_ax,
                segment_index=0,
            )

            if current_ax is None:
                plt.title(plot_title)
                plt.show()
            else:
                current_ax.set_title(plot_title)

        if as_subplot:
            plt.show()


def generate_subplot(
    steps: Union[List[str], str]
) -> Tuple[matplotlib.figure.Figure, NDArray[matplotlib.axes._axes.Axes], int, int]:
    """
    Generate the Matplotlib subplots figure, with hte number of
    columns fixed at two and the number of rows depending on the
    number of steps.

    Parameters
    ----------
    steps : Union[List[str], str]
        the preprocessing steps that will be plot.

    Returns
    -------
    fig : matplotlib.figure.Figure
        Matplotlib figure displaying the preprocessed data.

    ax :  NDArray[matplotlib.axes._axes.Axes]
        An array holding the axes objects in a plot / subplot.

    num_rows : int
    num_cols : int
        Number of rows and columns in the subplot, as determined
        by the number of processing steps to display.
    """
    num_cols = 2
    num_rows = np.ceil(len(steps) / num_cols).astype(int)
    fig, ax = plt.subplots(num_rows, num_cols)
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])

    return fig, ax, num_rows, num_cols


def get_subplot_ax(
    idx: int, ax: NDArray[matplotlib.axes._axes.Axes], num_rows: int, num_cols: int
) -> matplotlib.axes._axes.Axes:
    """
    Get the Axes object of the current axis to plot. As preprocessing
    steps are cycled through, axis are plot separately based on the
    current row / column needs to plot. We need to convert
    from subscript to linear indices to get the appropriate axis object.

    Parameters
    ----------
    idx : int
        Idx of the currently displayed preprocessing step.

    ax : NDArray[matplotlib.axes._axes.Axes]
        An array of axis objects on the plot / subplot.

    num_rows : int
    num_cols : int
        The number of rows and columns in the subplot (as determined by the
        number of preprocessing steps).

    Returns
    -------
    current_ax : matplotlib.axes._axes.Axes
        Axis to plot the current preprocessing step data on.
    """
    idx_unraveled = np.unravel_index(idx, shape=(num_rows, num_cols))
    current_ax = ax[idx_unraveled]
    return current_ax


def process_input_arguments(
    data: Union[PreprocessingData, SortingData],
    run_name: str,
    steps: Union[List[str], str],
    as_subplot: bool,
) -> Tuple[Union[List[str], str], bool]:
    """
    Check the passed configurations are valid.
    See `visualise()` for arguments.

    Returns
    -------
    steps : Dict
        `steps` as a List, checked for validity.

    as_subplot: bool
        `as_subplot`, possibly forced to False if the number
        of steps is only 1 (in which case subplot is redundant).
    """
    if not isinstance(steps, List):
        steps = [steps]

    if "all" in steps:
        assert len(steps) == 1, "if using 'all' only put one step input"
        steps = utils.get_keys_first_char(data[run_name])  # type: ignore

    assert len(steps) <= len(data[run_name]), (
        "The number of steps must be less or equal to the "
        "number of steps in the recording"
    )

    if len(steps) == 1 and as_subplot:
        as_subplot = False

    return steps, as_subplot


def validate_options_against_recording(
    recording: BaseRecording,
    data: Union[PreprocessingData, SortingData],
    run_name: str,
    time_range: Optional[Tuple],
) -> None:
    """
    Check the passed configurations are valid.
    See `visualise()` for arguments.

    TODO
    ----
    can't find a better way to get final timepoint,
    but must be somewhere, this is wasteful.
    """
    if isinstance(data, PreprocessingData):
        assert (
            run_name in data
        ), "The run_name must be a key in the loaded `preprocessing_data` dict."
    if time_range is not None:
        assert (
            time_range[1] <= recording.get_times(segment_index=0)[-1]
        ), "The time range specified is longer than the maximum time of the recording."
