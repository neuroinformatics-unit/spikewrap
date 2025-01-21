from __future__ import annotations
import matplotlib.pyplot as plt
import spikeinterface.full as si
from spikewrap.configs._backend import canon
import numpy as np
from spikewrap.utils import _utils


# TODO: need to test 4 shanks
def visualise_run_preprocessed(
    run_name,
    show,
    all_preprocessed,
    mode,
    time_range,
):
    """

    """

    # Setup subplots
    num_recordings = len(all_preprocessed)

    columns = np.ceil(np.sqrt(num_recordings)).astype(int)
    rows =  np.ceil(num_recordings / columns).astype(int)

    fig, axes = plt.subplots(rows, columns, figsize=(10 * columns, 6 * rows), squeeze=False)
    axes = axes.flatten()

    # Add spikeinterface plot_traces() plots to appropriate axis
    for i, (key, preprocessed) in enumerate(all_preprocessed.items()):
        ax = axes[i]

        recording_to_plot, _ = _utils.get_dict_value_from_step_num(
            preprocessed.data, "last"
        )

        si.plot_traces(
            recording_to_plot,
            order_channel_by_depth=True,
            time_range=time_range,
            return_scaled=True,
            show_channel_ids=True,
            mode=mode,
            ax=ax,
            segment_index=0,
        )
        if key == canon.grouped_shankname():
            ax.set_title(f"Run: {run_name}")  # Session: {ses_name}
        else:
            ax.set_title(f"Run: {run_name} Shank: {int(key) + 1}")  # Session: {ses_name}

    plt.tight_layout()

    if show:
        plt.show()

    return fig