# SST environment variables
CXX = $(shell sst-config --CXX)
CXXFLAGS = $(shell sst-config --ELEMENT_CXXFLAGS)
LDFLAGS  = $(shell sst-config --ELEMENT_LDFLAGS)

# Grab all the .cpp files, put objs and depends in the .build folder
SRC = $(wildcard *.cpp)
OBJ = $(SRC:%.cpp=.build/%.o)
DEP = $(OBJ:%.o=%.d)

# Tell Make that these are NOT files, just targets
.PHONY: all install uninstall clean test testRank% sst mpi-sst mpi-ahpgraph

# Simply typing "make" calls this by default, so everything gets build and installed
all: install

# Use the dependencies when compiling to check for header file changes
-include $(DEP)
.build/%.o: %.cpp
	@mkdir -p $(@D)
	$(CXX) $(CXXFLAGS) -MMD -c $< -o $@

# Link all the objects to create the library
libpingpong.so: $(OBJ)
	$(CXX) $(CXXFLAGS) $(LDFLAGS) -o $@ $^

# Register the model with SST
install: libpingpong.so
	sst-register pingpong pingpong_LIBDIR=$(CURDIR)

# Testing two ways, the testRank% will be described below
# Test will run pingpong.py with python and generate a flattened
# JSON file and DOT graph file
test: testRank0 testRank1 testRank2
	python3 pingpong.py

# The testRank% target allows for either sequential or parallel runs of
# these targets. If you run 'make test' then a JSON file for each rank will
# be generated sequentially, saving memory. If you run 'make test -j' then
# all the targets will run in separate threads allowing all JSON files to
# be generated at the same time, improving speed but taking more memory
testRank%:
	python3 pingpong.py --num=3 --rank=$* --partitioner=ahp_graph

sst: install
	sst pingpong.py

# arguments after '-- ' are passed to the sst model instead of taken by sst
# Number of mpi processes don't need to match the number of components we
# are making. For this example, since we have 8 ranks available and are
# creating 4 pingpongs, sst should put each device on a separate rank
# this means the Ping and Pong will be on different ranks within a single
# pingpong
mpi-sst: install
	mpirun -np 8 sst pingpong.py -- --num=4 --partitioner=sst

# arguments after '-- ' are passed to the sst model instead of taken by sst
# Since we are manually partitioning, we need the number of mpi processes
# to be greater than or equal to the number of ranks that we partition
# In this case each pingpong assembly is placed on a rank meaning there
# will be a Ping AND Pong on each rank
mpi-ahpgraph: install
	mpirun -np 8 sst --parallel-load=SINGLE pingpong.py -- --num=4 --partitioner=ahp_graph

# Unregister the model with SST
uninstall:
	sst-register -u pingpong

# Remove the build files and the library
clean: uninstall
	rm -rf __pycache__ .build *.so output
