from __future__ import annotations

import logging
import sys
import time


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level.upper())
        return
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s.%(msecs)03dZ level=%(levelname)s logger=%(name)s msg=%(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    formatter.converter = time.gmtime
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(level.upper())
