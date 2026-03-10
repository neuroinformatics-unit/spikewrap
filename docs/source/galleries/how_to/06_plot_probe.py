# ruff: noqa: E402
"""
How to Plot the Probe
=====================

This how-to demonstrates how to plot the probe. The probe
can also be saved to the session output folder. To get the
ProbeInterface object, use :class:`spikewrap.Session.get_probe()`

"""

import spikewrap as sw

session = sw.Session(
    subject_path=sw.get_example_data_path("openephys") / "rawdata" / "sub-001",
    session_name="ses-001",
    file_format="openephys",
    run_names="all"
)

fig = session.plot_probe(
    figsize=(12, 10),
    aspect_ratio=0.2
)
