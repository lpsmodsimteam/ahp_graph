"""Collection of Unit tests for AHPGraph SSTGraph."""

from AHPGraph import *
from AHPGraph.unittest.test import *
from AHPGraph.unittest.Devices import *

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='AHPGraph SSTGraph unittests')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='show detailed output')
    args = parser.parse_args()
    test.verbose = args.verbose
