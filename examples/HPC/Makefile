# Tell Make that these are NOT files, just targets
.PHONY: all clean test

# Simply typing "make" calls this by default
all: test

test:
	python3 HPC.py

# Remove the files
clean:
	rm -rf __pycache__ *.json *.dot *.svg *.png *.css
