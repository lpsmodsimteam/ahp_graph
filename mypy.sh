#!/usr/bin/env bash

export MYPYPATH=$MYPYPATH:$(pwd)/..
SourceFiles=(
    'src/ahp_graph/Device.py'
    'src/ahp_graph/DeviceGraph.py'
    'src/ahp_graph/SSTGraph.py'
)
UnitTestFiles=(
    'tests/Devices.py'
    'tests/test_Device.py'
    'tests/test_DeviceGraph.py'
)
ExampleFiles=(
    'examples/pingpong/python/architecture.py'
    'examples/pingpong/python/pingpong.py'
    'examples/pingpong/sst/pingpong.py'
    'examples/HPC/processor.py'
    'examples/HPC/server.py'
    'examples/HPC/HPC.py'
)

for file in "${SourceFiles[@]}"; do
    echo -e "$file"
    mypy $file
    echo
done

for file in "${UnitTestFiles[@]}"; do
    echo -e "$file"
    mypy $file
    echo
done

for file in "${ExampleFiles[@]}"; do
    echo -e "$file"
    mypy $file
    echo
done

rm -rf .mypy_cache
