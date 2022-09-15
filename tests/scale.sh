#!/usr/bin/env bash

rm results.txt
touch results.txt

for levels in {0..16}
do
	echo "Level: $levels" >> results.txt
	/usr/bin/time python3 scalability.py -l=$levels -a=4 >> results.txt 2>&1
	echo >> results.txt
done
