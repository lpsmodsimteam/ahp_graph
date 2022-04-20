# SST environment variables
CXX = $(shell sst-config --CXX)
CXXFLAGS = $(shell sst-config --ELEMENT_CXXFLAGS)
LDFLAGS  = $(shell sst-config --ELEMENT_LDFLAGS)

# Grab all the .cpp files, put objs and depends in the .build folder
SRC = $(wildcard *.cpp)
OBJ = $(SRC:%.cpp=.build/%.o)
DEP = $(OBJ:%.o=%.d)

# Tell Make that these are NOT files, just targets
.PHONY: all install uninstall clean test sst

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

test:
	python3 pingpong.py

sst: install
	sst pingpong.py

# Unregister the model with SST
uninstall:
	sst-register -u pingpong

# Remove the build files and the library
clean: uninstall
	rm -rf .build libpingpong.so *.json *.dot *.svg *.css
