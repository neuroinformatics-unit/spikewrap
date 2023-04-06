import matplotlib.pyplot as plt
import numpy as np
import spikeinterface.widgets as sw
import utils
from spikeinterface.core import order_channels_by_depth


def visualise(
    data,
    steps,
    mode="auto",
    as_subplot=False,
    channels_to_show=None,
    time_range=None,
    show_channel_ids=None,
):
    """
    channels to show must be indexes
    handle steps int vs. char...
    """
    if not isinstance(steps, list):
        steps = [steps]  # should take str or int

    if "all" in steps:
        assert (
            len(steps) == 1
        ), "if using 'all' only put one step input"  # need more validation...
        steps = utils.get_keys_first_char(data)

    if len(steps) == 1 and as_subplot:
        as_subplot = False  # TODO: or error?

    if channels_to_show is not None and not isinstance(channels_to_show, np.ndarray):
        channels_to_show = np.array(channels_to_show, dtype=np.int32)

    if as_subplot:
        num_cols = 2
        num_rows = np.ceil(len(steps) / num_cols).astype(int)
        fig, ax = plt.subplots(num_rows, num_cols)

    for idx, step in enumerate(steps):
        rec, full_key = utils.get_dict_value_from_step_num(data, str(step))

        if as_subplot:
            idx = np.unravel_index(idx, shape=(num_rows, num_cols))
            current_ax = ax[idx]
        else:
            current_ax = None

        if channels_to_show is None:
            channel_ids_to_show = None
        else:
            channel_ids = rec.get_channel_ids()

            order_f, order_r = order_channels_by_depth(
                recording=rec, dimensions=("x", "y")
            )

            channel_ids_to_show = channel_ids[order_f][channels_to_show]

        sw.plot_timeseries(
            rec,  # this takes a dict but just shows overlay
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
