#!/usr/bin/env bash

CYAN="\033[0;36m"
NC="\033[0m" # No Color - Default
FAIL="\033[0;31mFAIL\033[0m\n"
PASS="\033[0;32mPASS\033[0m\n"

FILES=("Device.py" "DeviceGraph.py" "SSTGraph.py")

while getopts vh flag; do
    case "${flag}" in
        v) verbose=" --verbose";;
        h) echo "optional flag -v to show verbose output"; exit;;
    esac
done

for file in "${FILES[@]}"; do
    echo -e "${CYAN}python3 ${file}${NC}${verbose}"
    python3 $file$verbose
    status=$?
    echo -en "${CYAN}${file}${NC} - "
    [ $status -eq 0 ] && echo -e ${PASS} || echo -e ${FAIL}
done
