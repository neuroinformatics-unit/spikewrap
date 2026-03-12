# There is a bug in Python 3.12/tcl/windows that leads to intermittent errors in tests, as described below:
# https://stackoverflow.com/questions/71443540/intermittent-pytest-failures-complaining-about-missing-tcl-files-even-though-the
# A quick workaround is to use a non-tkinter backend for the tests in this case.
import matplotlib

matplotlib.use("Agg")
