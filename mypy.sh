#!/usr/bin/env bash

export MYPYPATH=$MYPYPATH:$(pwd)/..
SourceFiles=(
    'ahp_graph/Device.py'
    'ahp_graph/DeviceGraph.py'
    'ahp_graph/SSTGraph.py'
)
UnitTestFiles=(
    'unittest/Devices.py'
    'unittest/test_Device.py'
    'unittest/test_DeviceGraph.py'
)
ExampleFiles=(
    'examples/pingpong/architecture.py'
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
