# Tell Make that these are NOT files, just targets
.PHONY: all clean test

# Simply typing "make" calls this by default
all: test

test:
	python3 HPC.py --dim=3x3 --nodes=16 --cores=8

# Remove the files
clean:
	rm -rf __pycache__ *.json *.dot *.svg *.png *.css
