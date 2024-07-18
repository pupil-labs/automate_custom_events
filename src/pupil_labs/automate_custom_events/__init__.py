"""Top-level entry-point for the automate_custom_events package"""

import sys

if sys.version_info < (3, 8):
    from importlib_metadata import PackageNotFoundError, version
else:
    from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pupil_labs_automate_custom_events")
except PackageNotFoundError:
    # package is not installed
    pass

__all__ = ["__version__"]