"""pytest setup: makes the stand-in omniscope.api and the harness importable for every block's tests."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(HERE, "tools", "python", "harness"), os.path.join(HERE, "tools", "python")):
    if p not in sys.path:
        sys.path.insert(0, p)
