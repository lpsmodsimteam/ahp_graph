# Tell Make that these are NOT files, just targets
.PHONY: all clean test sst

APPS=$(SST_ELEMENTS_HOME)/src/sst/elements/rdmaNic/tests/app/rdma
LIB=$(APPS)/librdma.a

# Simply typing "make" calls this by default
all: test testRank%

test: testRank0 testRank1 testRank2 testRank3

# The testRank% target allows for either sequential or parallel runs of
# these targets. If you run 'make test' then a JSON file for each rank will
# be generated sequentially, saving memory. If you run 'make test -j' then
# all the targets will run in separate threads allowing all JSON files to
# be generated at the same time, improving speed but taking more memory
testRank%:
	python3 HPC.py --rank=$*

# arguments after '-- ' are passed to the sst model instead of taken by sst
sst: $(LIB)
	sst HPC.py #-- --shape=3x3 --nodes=16 --cores=8

# arguments after '-- ' are passed to the sst model instead of taken by sst
mpi-sst: $(LIB)
	mpirun -np 4 sst HPC.py -- --partitioner=sst

# arguments after '-- ' are passed to the sst model instead of taken by sst
# since we are using threads, need to tell SST how many threads to use as well
# in this case, each node gets its own thread within a rank (rack)
# for the default case, this is 1 node per rack plus an extra thread for the
# router resulting in 2 threads required.
mpi-ahpgraph: $(LIB)
	mpirun -np 4 sst -n2 --parallel-load=SINGLE HPC.py -- --partitioner=ahp_graph

$(LIB):
	make -C $(APPS) all

# Remove the files
clean:
	rm -rf __pycache__ output *.VanadisNodeOS
