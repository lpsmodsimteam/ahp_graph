# Tell Make that these are NOT files, just targets
.PHONY: all clean test

# Simply typing "make" calls this by default
all: test

test:
	python3 pingpong.py

# Remove the files
clean:
	rm -rf __pycache__ output
