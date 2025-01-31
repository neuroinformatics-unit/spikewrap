from __future__ import annotations

from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
import spikeinterface.full as si

from spikewrap.configs._backend import canon
from spikewrap.utils import _utils


def visualise_run_preprocessed(
    run_name: str,
    show: bool,
    all_preprocessed: dict,
    ses_name: str,
    mode: Literal["map", "line"],
    time_range: tuple[float, float],
    show_channel_ids: bool,
    figsize: tuple[int, int],
):
    """
    Visualise preprocessed recordings for a given run.

    Creates a grid of subplots to display shanks (if split by shank) from
    preprocessed recordings using SpikeInterface's `plot_traces()` function.

    Parameters
    ----------
    run_name
        The name of the runs.
    show
        If True, display the plot immediately.
    all_preprocessed
        Preprocessed._data dict of preprocessed recording objects.
    ses_name
        Name of the parent session for this run.
    mode
        Visualization mode for traces, as supported by SpikeInterface.
    time_range
        Time range (start, end) to visualise in seconds.
    show_channel_ids
        If True, display channel IDs on the plots.
    figsize
        Size of each subplot in inches (width, height).

    Returns
    -------
    fig
        The matplotlib Figure object containing the grid of plots.

    """

    # Setup subplots
    num_recordings = len(all_preprocessed)

    columns = np.ceil(np.sqrt(num_recordings)).astype(int)
    rows = np.ceil(num_recordings / columns).astype(int)

    fig, axes = plt.subplots(
        rows, columns, figsize=(figsize[0] * columns, figsize[1] * rows), squeeze=False
    )
    axes = axes.flatten()

    # Add spikeinterface plot_traces() plots to appropriate axis
    for i, (key, preprocessed) in enumerate(all_preprocessed.items()):
        ax = axes[i]

        recording_to_plot, _ = _utils._get_dict_value_from_step_num(
            preprocessed._data, "last"
        )

        si.plot_traces(
            recording_to_plot,
            order_channel_by_depth=True,
            time_range=time_range,
            return_scaled=True,
            show_channel_ids=show_channel_ids,
            mode=mode,
            ax=ax,
            segment_index=0,
        )
        if key == canon.grouped_shankname():
            ax.set_title(f"Session: {ses_name}, Run: {run_name}")
        else:
            ax.set_title(f"Session: {ses_name}, Run: {run_name} Shank: {int(key) + 1}")

    plt.tight_layout()

    if show:
        plt.show()

    return fig
