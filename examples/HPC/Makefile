# Tell Make that these are NOT files, just targets
.PHONY: all clean test sst

APPS=$(SST_ELEMENTS_HOME)/src/sst/elements/rdmaNic/tests/app/rdma
LIB=$(APPS)/librdma.a

# Simply typing "make" calls this by default
all: test

test:
	python3 HPC.py #--shape=3x3 --nodes=16 --cores=8

sst: $(LIB)
	# arguments after '-- ' are passed to the sst model instead of taken by sst
	sst HPC.py #-- --shape=3x3 --nodes=16 --cores=8

mpi-sst: $(LIB)
	# arguments after '-- ' are passed to the sst model instead of taken by sst
	mpirun -np 4 sst HPC.py -- --partitioner=sst

mpi-pydl: $(LIB)
	# arguments after '-- ' are passed to the sst model instead of taken by sst
	mpirun -np 4 sst --parallel-load=SINGLE HPC.py -- --partitioner=pydl

$(LIB):
	make -C $(APPS) all

# Remove the files
clean:
	rm -rf __pycache__ *.json *.dot *.svg *.png *.css *.VanadisNodeOS
