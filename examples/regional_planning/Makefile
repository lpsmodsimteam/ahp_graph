CXX=$(shell sst-config --CXX)
CXXFLAGS=$(shell sst-config --ELEMENT_CXXFLAGS)
LDFLAGS=$(shell sst-config --ELEMENT_LDFLAGS)

ifndef CONFIG
CONFIG=create_graph
$(info no "CONFIG" was provided, so defaulting to "create_graph")
endif

# as per https://stackoverflow.com/a/11843480/1164295
# shared object library must start with "lib"
all: libhouse.so libneighborhood.so libcity.so install picture

clean:
	rm -rf *.o *.so *.png *.gv output/ __pycache__/ html/ latex/


#.PHONY: libhouse.so
libhouse.so: component_house.cpp\
	            component_house.hpp
	$(CXX) $(CXXFLAGS) $(LDFLAGS) -o $@ $<

#.PHONY: libcity.so
libcity.so: component_city.cpp\
	            component_city.hpp
	$(CXX) $(CXXFLAGS) $(LDFLAGS) -o $@ $<

#.PHONY: libneighborhood.so
libneighborhood.so: component_neighborhood.cpp\
	            component_neighborhood.hpp
	$(CXX) $(CXXFLAGS) $(LDFLAGS) -o $@ $<

install: libhouse.so libcity.so libneighborhood.so 
	sst-register city city_LIBDIR=$(CURDIR)
	sst-register neighborhood neighborhood_LIBDIR=$(CURDIR)
	sst-register house house_LIBDIR=$(CURDIR)

picture: install
	sst --output-dot=$(CONFIG).gv --run-mode=init $(CONFIG).py
	dot $(CONFIG).gv -Tpng > $(CONFIG).png

run: install
	time sst $(CONFIG).py

mpirun: install
	time mpirun -np 2 sst $(CONFIG).py


documentation:
	doxygen

