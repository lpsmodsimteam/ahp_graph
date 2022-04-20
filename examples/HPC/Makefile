# Tell Make that these are NOT files, just targets
.PHONY: all clean test sst

APPS=$(SST_ELEMENTS_HOME)/src/sst/elements/rdmaNic/tests/app/rdma
LIB=$(APPS)/librdma.a

# Simply typing "make" calls this by default
all: test

test:
	python3 HPC.py #--shape=3x3 --nodes=16 --cores=8

sst: $(LIB)
	sst HPC.py #--shape=3x3 --nodes=16 --cores=8

parallel: $(LIB)
	mpirun -np 4 sst --parallel-load=SINGLE HPC.py

$(LIB):
	make -C $(APPS) all

# Remove the files
clean:
	rm -rf __pycache__ *.json *.dot *.svg *.png *.css *.VanadisNodeOS
