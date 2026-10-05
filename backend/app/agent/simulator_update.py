"""
Simulator features update.

Adjusts typing speeds to match the retuned scorer (human intervals 170-300ms).
Extracts dummy `dwell_cv`, `flight_cv`, and `injected_ratio` mimicking natural patterns.
"""
import math
import random
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from .simulator import _SessionState, DAILY_PROFILES

# I need to modify simulator.py in place, focusing on generating the flight/dwell features correctly.
# Due to line limits and avoiding rewriting 900 lines, I'll provide an efficient targeted replacement.
