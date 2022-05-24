"""Collection of Unit tests for AHPGraph SSTGraph."""

from AHPGraph import *
from AHPGraph.unittest.test import *
from AHPGraph.unittest.Devices import *


def AttributeTest() -> bool:
    """Test of DeviceGraph with attributes."""
    t = test('AttributeTest')

    attr = {'a1': 1, 'a2': 'blue', 'a3': False}
    graph = DeviceGraph(attr)
    t.test(graph.attr == attr, 'attr')

    return t.finish()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='AHPGraph SSTGraph unittests')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='show detailed output')
    args = parser.parse_args()
    test.verbose = args.verbose

    results = [AttributeTest()]

    exit(1 if True in results else 0)
