#!/usr/bin/env python3
"""NEON RUSH autoplay — thin wrapper.

See ai/autoplay.py for the full implementation.
Usage: python3 autoplay.py [--headless] [--grid] [-s SPEED] [-r RUNS] [--learn] [--god] [--evo]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai.autoplay import main

if __name__ == "__main__":
    sys.exit(main())
