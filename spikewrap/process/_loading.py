from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

    from probeinterface import Probe
    from spikeinterface.core import BaseRecording

import re
import warnings

import spikeinterface.extractors as si_extractors

from spikewrap.utils import _utils


def load_data(
    run_path: Path, file_format: Literal["spikeglx", "openephys"], probe: Probe | None
) -> tuple[BaseRecording, BaseRecording]:
    """
    TODO: add note that must juggle two recordings has probe is not loaded on sync recording!

    """
    _utils.message_user(f"Loading data from path: {run_path}")

    if file_format == "spikeglx":
        without_sync, with_sync = [
            si_extractors.read_spikeglx(
                folder_path=run_path,
                stream_id="imec0.ap",
                all_annotations=True,
                load_sync_channel=sync,
            )
            for sync in [False, True]
        ]

    elif file_format == "openephys":
        is_legacy_format = any(run_path.rglob("structure.openephys"))
        if is_legacy_format:
            raise RuntimeError(
                "Legacy OpenEphys format is not supported. "
                "Please contact the spikewrap team if you would like to see this supported."
            )

        without_sync = si_extractors.read_openephys(
            folder_path=run_path,
            all_annotations=True,
            load_sync_channel=False,
        )
        try:
            with_sync = si_extractors.read_openephys(
                folder_path=run_path,
                all_annotations=False,
                load_sync_channel=True,
            )
        except ValueError:
            with_sync = None

    else:
        raise ValueError("Raw data type not recognised. Please contact spikewrap team.")

    if without_sync.get_num_segments() > 1:
        raise RuntimeError(
            f"Data at\n{run_path}\nhas multiple segments. "
            f"This should nto be the case. "
            f"Each run must contain only 1 recording."
        )

    if probe is not None:
        if without_sync.has_probe():
            raise RuntimeError(
                "A probe was already auto-detected. Cannot manually set probe. "
                "Please contact spikewrap if required."
            )
        without_sync = without_sync.set_probe(probe)

    if not without_sync.has_probe():
        raise RuntimeError(
            "No probe is attached to this recording. Pass a `probe` object to set."
            "See ProbeInterface for available probes."
        )

    return without_sync, with_sync


# -----------------------------------------------------------------------------
# Get Run Paths
# -----------------------------------------------------------------------------
# These functions encode the rules for run detection from spikeglx and
# openephys datasets, as described in the documentation. They must reflect
# exactly the process described in the documentation.


def get_raw_run_paths(
    file_format: Literal["spikeglx", "openephys"],
    ses_path: Path,
    passed_run_names: Literal["all"] | list[str],
) -> list[Path]:
    """
    Get the full filepath to recording runs from spikeglx or openephys data.

    Parameters
    ----------
    file_format
        The data format of the electrophysiology recordings.
    ses_path
        The path to the session for which to detect the runs.
    passed_run_names
        The ordered names of the runs to retrieve. If "all", all detected runs are returned.
        Otherwise, each run name in the list must match a detected run in the folders.

    Returns
    -------
    list of Path
        A list of validated run paths, each contain one recording.
    """

    # Handle the NeuroBlueprint case
    ephys_path = list(ses_path.glob("ephys"))
    if len(ephys_path) == 1:
        ses_path = ses_path / "ephys"

    if file_format == "spikeglx":
        detected_run_paths = get_spikeglx_runs(ses_path)

    elif file_format == "openephys":
        detected_run_paths = get_openephys_runs(ses_path)
    else:
        raise ValueError("`file_format` not recognised.")

    if passed_run_names == "all":
        run_paths = detected_run_paths
    else:
        detected_runs = {path_.name: path_ for path_ in detected_run_paths}

        for passed_name in passed_run_names:
            if passed_name not in detected_runs:
                raise ValueError(f"{passed_name} not found in folder: {ses_path}")

        # We need to maintain the same order as `passed_run_names`
        run_paths = [detected_runs[name] for name in passed_run_names]

    if not _utils._paths_are_in_datetime_order(run_paths, "creation"):
        warnings.warn(
            f"The sessions or runs provided for are not in creation datetime order.\n"
            f"They will be concatenated in the order provided, as:\n"
            f"{[path_.name for path_ in run_paths]}."
        )

    return run_paths


def get_spikeglx_runs(ses_path: Path) -> list[Path]:
    """
    Detect and validate runs from SpikeGLX recordings.

    Does not support more than one imec probe, nor multi-trigger recordings.
    All folders at the run level will be treated as separate runs, ignoring gate number.

    Parameters
    ----------
    ses_path
        The path to the session for which to detect the runs.

    Returns
    -------
    list of Path
        A list of validated run paths, each contain one recording.
    """

    # Look for spikeglx runs, either folders at the session level that include
    # pattern like "g0_imec" or contain a folder that does.
    putative_run_paths = [path_ for path_ in ses_path.glob("*") if path_.is_dir()]
    detected_run_paths = []

    for path_ in putative_run_paths:

        # If the run contains spikeglx files
        if any(path_.glob("*.ap.bin")):
            detected_run_paths.append(path_)

        # Otherwise if the putative run folder contains a
        # spikeglx-formatted folder then it is a run folder
        # (spikeinterface will auto-detect data recursively from
        # this folder down, which is why we only allow one folder
        # within the run folder in this case.
        else:
            subpath_ = list(path_.glob("*g*imec*"))
            if any(subpath_):
                if not len(subpath_) == 1:
                    raise RuntimeError(
                        f"Multiple gates / triggers are not supported. Only one folder"
                        f"expected in path: {path_}"
                    )
            detected_run_paths.append(path_)

    # Currently, only imec0 supported
    for path_ in detected_run_paths:
        putative_imec_id = path_.name.split("-")[-1]
        match = re.compile(r".*_imec(\d+)$").match(putative_imec_id)

        if match and match.group(1) != "0":
            raise RuntimeError(
                f"The foldername {path_.name} has a id which is not imec0.\n"
                f"This run is at path: {ses_path}\n"
                f"This is not currently supported. Please contact the spikewrap team."
            )

    if not any(detected_run_paths):
        raise FileNotFoundError(f"No spikeglx run folders found at {ses_path}.")

    # Currently, multi-trigger not supported
    for path_ in detected_run_paths:
        rec_paths = list(
            path_.rglob("*ap.bin")  # currently LFP not supported.
        )  # rglob as we might have two-level run folder (TODO: DOC)
        if len(rec_paths) > 1:
            raise RuntimeError(
                f"The run folder {path_} contains more than one recording.\n"
                f"Currently multi-trigger recordings are not supported.\n"
                f"Please contact the spikerwap team."
            )

        if len(rec_paths) == 0:
            raise RuntimeError(f"No recording found in run path: {path_}")

    return detected_run_paths


def get_openephys_runs(ses_path: Path) -> list[Path]:
    """
    Detect and validate runs from OpenEphys recordings.

    Multiple Record Node's and `experiments` are not supported.
    `recordings` within the `experiments1` folder are treated as runs.

    Parameters
    ----------
    ses_path
        The path to the session for which to detect the runs.

    Returns
    -------
    list of Path
        A list of validated run paths, each contain one recording.
    """
    node_path = list(ses_path.glob("*Node*"))

    if len(node_path) > 1:
        raise RuntimeError(
            f"Only single-Node openephys recordings currently supported.\n"
            f"Multiple found at {ses_path}\n",
            "Please contact the spikewrap team.",
        )

    if len(node_path) == 0:
        raise RuntimeError(f"No 'Node' openephys recordings found at {ses_path}.")

    experiment_path = list(node_path[0].glob("*experiment*"))

    if len(experiment_path) > 1:
        raise RuntimeError(
            f"Only single-'experiment' openephys recordings currently supported.\n"
            f"Multiple found at {node_path}\n"
            f"Please contact the spikewrap team."
        )

    if len(experiment_path) == 0:
        raise RuntimeError(
            f"No 'experiment' openephys recordings found at {node_path}."
        )

    detected_run_paths = [
        path_ for path_ in experiment_path[0].glob("*recording*") if path_.is_dir()
    ]

    for path_ in detected_run_paths:
        rec_paths = list(path_.glob("*continuous*"))
        if len(rec_paths) == 0:
            raise RuntimeError(f"No 'continuous' recording found in run path: {path_}")

    return detected_run_paths
