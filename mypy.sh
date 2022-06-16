#!/usr/bin/env bash

export MYPYPATH=$MYPYPATH:$(pwd)/..
SourceFiles=(
    'Device.py'
    'DeviceGraph.py'
    'SSTGraph.py'
)
UnitTestFiles=(
    'unittest/test.py'
    'unittest/Devices.py'
    'unittest/Device.py'
    'unittest/DeviceGraph.py'
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
    mypy $file \
        # --disable-error-code arg-type \
        # --disable-error-code operator \
        # --disable-error-code index \
        # --disable-error-code union-attr
    echo
done

for file in "${ExampleFiles[@]}"; do
    echo -e "$file"
    mypy $file \
        # --disable-error-code arg-type \
        # --disable-error-code operator \
        # --disable-error-code index \
        # --disable-error-code union-attr \
        # --disable-error-code misc
    echo
done

rm -rf .mypy_cache
