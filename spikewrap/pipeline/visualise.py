from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import spikeinterface.widgets as sw

from ..data_classes.preprocessing import PreprocessingData
from ..data_classes.sorting import SortingData
from ..utils import utils
from .sort import get_sorting_data_class

if TYPE_CHECKING:
    import matplotlib
    from numpy.typing import NDArray
    from spikeinterface.core import BaseRecording


def visualise(
    data: Union[PreprocessingData, SortingData],
    sessions_and_runs: Dict,
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
    if not isinstance(steps, List):
        steps = [steps]

    for ses_name in sessions_and_runs.keys():
        for run_name in sessions_and_runs[ses_name]:
            first_key = list(data[ses_name][run_name].keys())[-1]
            total_used_shanks = np.unique(
                data[ses_name][run_name][first_key].get_property("group")
            ).size  # TODO

            if "all" in steps:
                assert len(steps) == 1, "if using 'all' only put one step input"
                steps = utils.get_keys_first_char(
                    data[ses_name][run_name]  # type: ignore
                )

            plot_subplot = as_subplot
            if len(steps) == 1 and as_subplot:
                plot_subplot = False

            assert len(steps) <= len(data[ses_name][run_name]), (
                "The number of steps must be less or equal to the "
                "number of steps in the recording"
            )

            for shank_idx in range(total_used_shanks):
                if plot_subplot:
                    fig, ax, num_rows, num_cols = generate_subplot(steps)

                for idx, step in enumerate(steps):
                    recording, full_key = utils.get_dict_value_from_step_num(
                        data[ses_name][run_name], str(step)
                    )

                    validate_options_against_recording(recording, time_range)

                    recordings = recording.split_by(property="group")
                    recording_to_plot = recordings[shank_idx]

                    plot_title = make_preprocessing_plot_title(
                        f"ses: {ses_name}, run: {run_name}",
                        full_key,
                        shank_idx,
                        recording_to_plot,
                        total_used_shanks,
                    )

                    current_ax = (
                        None
                        if not plot_subplot
                        else get_subplot_ax(idx, ax, num_rows, num_cols)
                    )

                    sw.plot_timeseries(
                        recording_to_plot,
                        order_channel_by_depth=True,
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

                if plot_subplot:
                    plt.show()


def visualise_preprocessed(
    base_path,
    sub_name,
    sessions_and_runs,
    concatenate_sessions,
    concatenate_runs,
    mode: str = "auto",
    time_range: Optional[Tuple] = None,
    show_channel_ids: bool = False,
):
    SortingDataClass = get_sorting_data_class(
        concatenate_sessions,
        concatenate_runs,
    )

    sorting_data = SortingDataClass(
        base_path,
        sub_name,
        sessions_and_runs,
        sorter="placeholder",
        print_messages=False,
    )
    # TODO: this automatically splits by group, the main pipeline does not....

    for ses_name in sorting_data.keys():
        for run_name in sorting_data[ses_name].keys():
            total_used_shanks = np.unique(
                sorting_data[ses_name][run_name].get_property("group")
            ).size

            # TODO: the below is a direct copy from above! Try and merge
            # these as best possible... !!
            # !!
            # !!
            for shank_idx in range(total_used_shanks):
                recording = sorting_data[ses_name][run_name]

                recordings = recording.split_by(property="group")
                recording_to_plot = recordings[shank_idx]

                plot_title = make_preprocessing_plot_title(
                    f"ses: {ses_name}, run: {run_name}",
                    "",
                    shank_idx,
                    recording_to_plot,
                    total_used_shanks,
                )

                sw.plot_timeseries(
                    recording_to_plot,
                    order_channel_by_depth=True,
                    time_range=time_range,
                    return_scaled=True,
                    show_channel_ids=show_channel_ids,
                    mode=mode,
                    ax=None,
                    segment_index=0,
                )

                plt.title(plot_title)
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


def validate_options_against_recording(
    recording: BaseRecording,
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
    if time_range is not None:
        assert (
            time_range[1] <= recording.get_times(segment_index=0)[-1]
        ), "The time range specified is longer than the maximum time of the recording."


def make_preprocessing_plot_title(
    run_name: str,
    full_key: str,
    shank_idx: int,
    recording_to_plot: BaseRecording,
    total_used_shanks: int,
) -> str:
    """
    For visualising data, make the plot titles (with headers in bold). If
    more than one shank is used, the title will also contain information
    on the displayed shank.

    Parameters
    ----------
    run_name : str
        The name of the preprocessing run (e.g. "1-phase_shift").

    full_key : str
        The full preprocessing key (as defined in preprocess.py).

    shank_idx : int
        The SpikeInterface group number representing the shank number.

    recording_to_plot : BaseRecording
        The SpikeInterface recording object that is being displayed.

    total_used_shanks : int
        The total number of shanks used in the recording. For a 4-shank probe,
        this could be between 1 - 4 if not all shanks are mapped.

    Returns
    -------
    plot_title : str
        The formatted plot title.
    """
    plot_title = (
        r"$\bf{Run \ name:}$" + f"{run_name}"
        "\n" + r"$\bf{Preprocessing \ step:}$" + f"{full_key}"
    )
    if total_used_shanks > 1:
        plot_title += (
            "\n"
            + r"$\bf{Shank \ group:}$"
            + f"{shank_idx}, "
            + r"$\bf{Num \ channels:}$"
            + f"{recording_to_plot.get_num_channels()}"
        )
    return plot_title
