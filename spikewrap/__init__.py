from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("swc_epys")
except PackageNotFoundError:
    # package is not installed
    pass
