
Tested with SST-core v12.0 

The concept of "assemblies" is introduced in the context of houses being part of neighborhoods.

TODO: the concept of mixed fidelity is demonstrated. Abstractions used in the Python driver file (neighborhoods as classes) can be mixed with neighborhoods-as-SST-components. 



In the highest fidelity model, a "neighborhood" is an abstraction used in the SST Python driver file where
 a neighborhood has one or more houses
and a "city" is an abstraction that has one or more neighborhoods

To tune one aspect of simulation fidelity, the neighborhood can be an SST component, and the city can be an SST component.

# Example 1: a neighborhood with three houses

To run this model, use

    make

Here the "house" component inherits from "building" and "weather"

An example neighborhood comprised of SST components would be

          +---------+
          | house_0 |
          +---------+
          |         |
    +-----+---+     ++---------+
    | house_1 |      | house_2 |
    +---------+------+---------+

In the example above, the houses are fully connected by roads.

( ASCII art is from http://asciiflow.com/ )

The Python driver file for SST is already becoming unwieldy and the graph is relatively small!

# Example 2: assemblies as abstractions in the SST Python driver file

To run this model, use

    make

To create UML diagrams of the respective inheritances for C++ and Python

    doxygen -g

then follow https://stackoverflow.com/a/9488742/1164295

Four neighborhoods could be

                                                                   +----------------+
                                                                   | house_0        |
    +---------------+----------------+-----------------------------+ neighborhood_1 |
    |               | house_0        |                             +----------------+-----------+
    |     +---------+ neighborhood_0 +-+                       +---+                            |
    |     |         +----------------+ |                       |                                |
    |     |                            |                       |   +----------------+     +-----+----------+
    |    ++----------------+         +-+--------------+        |   | house_1        |     | house_2        |
    |    |  house_1        |         | house_2        |        |   | neighborhood_1 +-----+ neighborhood_1 |
    |    |  neighborhood_0 |         | neighborhood_0 |        |   +----------------+     +----------------+
    |    +-----------------+         +----------------+        |
    |                                                          +-------+
    |                                                                  |
    |                        +-------------------------------------+---+------------+
    |        +----------------+                                    | house_0        +---------------+
    +--------+ house_0        +-----+                           +--+ neighborhood_3 |               |
             | neighborhood_2 |     |                           |  +----------------+               |
             ++---------------+     |                           |                                   |
              |                   +-+--------------+            |                              +----+-----------+
              |                   | house_2        |            +----------------+             | house_2        |
       +------+---------+         | neighborhood_2 |            | house_1        +-------------+ neighborhood_3 |
       | house_1        +---------+----------------+            | neighborhood_3 |             +----------------+
       | neighborhood_2 |                                       +----------------+
       +----------------+

the computational cost of this increased scaling could be problematic. 
Therefore, replacing some of the neighborhoods with a single SST component would be useful.

# Example 3: mixed fidelity of houses and neighborhoods

To use this model, run

    make

With a mixed fidelity,

                                                                   +----------------+
                                                                   | house_0        |
    +---------------+----------------+-----------------------------+ neighborhood_1 |
    |               | house_0        |                             +----------------+-----------+
    |     +---------+ neighborhood_0 +-+                       +---+                            |
    |     |         +----------------+ |                       |                                |
    |     |                            |                       |   +----------------+     +-----+----------+
    |    ++----------------+         +-+--------------+        |   | house_1        |     | house_2        |
    |    |  house_1        |         | house_2        |        |   | neighborhood_1 +-----+ neighborhood_1 |
    |    |  neighborhood_0 |         | neighborhood_0 |        |   +----------------+     +----------------+
    |    +-----------------+         +----------------+        |
    |                                                          +-------+
    |                                                                  |
    |                        +-------------------------------------+---+------------+
    |        +----------------+                                    |                |
    +--------+                |                                    | neighborhood_3 |
             | neighborhood_2 |                                    +----------------+
             +----------------+




