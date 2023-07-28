from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import jax.numpy as jnp
import numpy as np
from jax import jit, vmap
from jax.lax import scan

from ..utils import utils

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from spikeinterface import WaveformExtractor


def get_waveform_similarity(
    waveforms: WaveformExtractor, unit_id: int, backend: Literal["numpy", "jax"] = "jax"
):
    """
    Calculate a num_waveform x num_waveform matrix containing
    cosine similarity between all waveforms for a unit. The waveforms
    are saved as 3d array (num_waveforms x num_samples x num_channels) by
    SpikeInterface, and waveforms are averaged across the channels
    where the signal is strongest (see `get_times_of_waveform_spikes()`)
    prior to cosine similarity calculation.

    waveforms : WaveformExtractor
        Spikeinterface WaveformExtractor object.

    unit_id : int
        ID of the unit to calculate the similarity matrix for.

    backend : Literal["jax", "numpy"]
        The backend with which to run waveform comparisons. Jax is around 50
        times faster in this case.
    """
    waveforms_data = waveforms.get_waveforms(unit_id=unit_id)

    if waveforms_data.shape[0] < 2:
        utils.message_user(
            f"Skipping {unit_id} as one or less waveforms detected for this unit."
        )
        return False, False

    selected_waveform_peak_times = get_times_of_waveform_spikes(waveforms, unit_id)

    assert (
        waveforms_data.shape[0] == selected_waveform_peak_times.size
    ), "Number of waveform peak times does not match number of extracted waveforms."

    if backend == "numpy":
        similarity_matrix = calculate_similarity_numpy(waveforms_data)
    elif backend == "jax":
        similarity_matrix = calculate_similarity_jax(waveforms_data)
    else:
        raise ValueError("`backend` must be: 'jax' or 'numpy'")

    return similarity_matrix, selected_waveform_peak_times


def get_times_of_waveform_spikes(waveforms, unit_id):
    """
    Extract the peak times of the waveforms that were randomly sampled.
    SpikeInterface WaveformExtractor randomly samples a set of spikes
    from all spikes in a unit (default 500) to reduce computation time
    and memory footprint. As such, the index of the sampled waveforms
    is used in the list of all spike times to find the sampled spike times.

    TODO
    ----
    Check manually that the correct spike times are extracted, as compared with Phy.
    """
    select_waveform_tuples = waveforms.get_sampled_indices(unit_id)
    try:
        select_waveform_idxs, seg_idxs = zip(*select_waveform_tuples)
    except:
        breakpoint()
    assert np.all(np.array(seg_idxs) == 0), "Multi-segment waveforms not tested."

    all_waveform_peak_idxs = waveforms.sorting.get_unit_spike_train(unit_id)
    selected_waveform_idxs = all_waveform_peak_idxs[np.array(select_waveform_idxs)]
    selected_waveform_peak_times = selected_waveform_idxs / waveforms.sampling_frequency

    return selected_waveform_peak_times


# --------------------------------------------------------------------------------------
# Similarity Matrix Calculators
# --------------------------------------------------------------------------------------


@jit
def calculate_similarity_jax(waveforms_data):
    """
    Speed up calculation of similarity matrix using Jax. First, average
    the waveforms across the best channels (where the waveform signal
    is strongest) for the unit. Then, define a vmapped function that
    calculates the cosine similarity between a waveform and every
    other waveform. Finally, use scan to replicate a for-loop
    over every waveform.

    Note that this redundantly calculates the upper and lower traingular
    of the similarity matrix, but this is necessary to take advantage of vmap
    speed-ups.

    Parameters
    ----------
    waveforms_data : Jax.Array
        A num_waveforms x num_samples x num_channels array containing
        data of all waveforms.

    Returns
    -------
    similarity_matrix : Jax.Array
        num_waveform x num_waveform matrix of cosine similarities
        for the unit.
    """
    averaged_waveforms = jnp.mean(waveforms_data, axis=2)

    def func(carry, i):
        y = averaged_waveforms[i, :]

        sim_matrix_row = vmap(
            lambda x: jnp.dot(x, y.T) / (jnp.linalg.norm(x) * jnp.linalg.norm(y)),
            in_axes=0,
        )(averaged_waveforms)

        return carry, sim_matrix_row

    similarity_matrix = scan(
        func, averaged_waveforms, np.arange(averaged_waveforms.shape[0])
    )[1]

    return similarity_matrix


def calculate_similarity_numpy(waveforms_data: NDArray):
    """
    The similarity matrix is calculated by filling the
    upper triangular only then copying to the lower triangular.

    Parameters
    ----------

    waveforms_data : NDArray
    A num_waveforms x num_samples x num_channels array containing
    data of all waveforms.

    Returns
    -------

    similarity_matrix : NDArray
    num_waveform x num_waveform matrix of cosine similarities
    for the unit.
    """
    num_spikes = waveforms_data.shape[0]
    averaged_waveforms = np.mean(waveforms_data, axis=2)

    similarity_matrix = np.zeros((num_spikes, num_spikes))
    for j in range(num_spikes):
        for i in range(j + 1):
            x = averaged_waveforms[i, :]
            y = averaged_waveforms[j, :]

            similarity_matrix[i, j] = np.dot(x, y.T) / (
                np.linalg.norm(x) * np.linalg.norm(y)
            )

    i_lower = np.tril_indices(similarity_matrix.shape[0], -1)
    similarity_matrix[i_lower] = similarity_matrix.T[i_lower]

    return similarity_matrix
