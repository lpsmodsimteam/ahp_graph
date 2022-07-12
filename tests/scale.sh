#!/usr/bin/env bash

rm results.txt
touch results.txt

for levels in {1..22}
do
	echo "Level: $levels" >> results.txt
	/usr/bin/time python3 scalability.py -l=$levels >> results.txt 2>&1
	echo >> results.txt
done
