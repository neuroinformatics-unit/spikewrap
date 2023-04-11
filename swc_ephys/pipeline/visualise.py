from typing import List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import spikeinterface.widgets as sw

from ..utils import utils
from .data_class import Data


def visualise(
    data: Data,
    steps: Union[List, str] = "all",
    mode: str = "auto",
    as_subplot: bool = False,
    channel_idx_to_show: Union[List, Tuple, np.ndarray, None] = None,
    time_range: Optional[Tuple] = None,
    show_channel_ids: bool = False,
):
    """
    Plot the data at various preprocessing steps, useful for quality-checking.
    Takes the pipeline.data_class.Data object (output from pipeline.preprocess).
    Channels are displayed ordered by depth. Note preprocessing is lazy, and only the
    section if data displayed will be preprocessed.

    If multiple preprocessing steps are shown, they will be placed in subplots
    on a single plot if as_subplots is True, otherwise in separate plots.

    data : swc_ephys Data class containing the preprocessing output (a dict
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
    """
    if not isinstance(steps, list):
        steps = [steps]

    if "all" in steps:
        # TODO: need more validation
        assert len(steps) == 1, "if using 'all' only put one step input"
        steps = utils.get_keys_first_char(data)

    if len(steps) == 1 and as_subplot:
        as_subplot = False

    if channel_idx_to_show is not None and not isinstance(
        channel_idx_to_show, np.ndarray
    ):
        channel_idx_to_show = np.array(channel_idx_to_show, dtype=np.int32)

    if as_subplot:
        num_cols = 2
        num_rows = np.ceil(len(steps) / num_cols).astype(int)
        fig, ax = plt.subplots(num_rows, num_cols)

    for idx, step in enumerate(steps):
        recording, full_key = utils.get_dict_value_from_step_num(data, str(step))

        if as_subplot:
            idx = np.unravel_index(idx, shape=(num_rows, num_cols))
            current_ax = ax[idx]
        else:
            current_ax = None

        if channel_idx_to_show is None:
            channel_ids_to_show = None
        else:
            channel_ids = recording.get_channel_ids()

            # channel ids are returned in default order (e.g. 0, 1, 2...)
            # not ordered by depth.
            channel_ids_to_show = channel_ids[channel_idx_to_show]

        sw.plot_timeseries(
            recording,
            channel_ids=channel_ids_to_show,
            order_channel_by_depth=True,
            time_range=time_range,
            return_scaled=True,
            show_channel_ids=show_channel_ids,
            mode=mode,
            ax=current_ax,
        )

        if not as_subplot:
            plt.title(full_key)
            plt.show()
        else:
            current_ax.set_title(full_key)

    if as_subplot:
        plt.show()
