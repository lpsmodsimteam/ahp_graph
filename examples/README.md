# examples of how to use `ahp_graph`

## Ping Pong

## HPC

## Regional planning

A city is comprised of neighborhoods connected by roads, and neighborhoods are comprised of houses connected by roads.

This model demonstrates the relation of assemblies and components. 


# (components and assemblies) versus (subcomponents and components)


+--------------------+
| assembly           |
|                    |
|  +---------------+ |
|  | assembly      | |
|  |               | |
|  | +-----------+ | |
|  | | component +-+-+------
|  | +-----------+ | |
|  |               | |
|  | +-----------+ | |
|  | | component +-+-+------
|  | +-----------+ | |
|  |               | |
|  | +-----------+ | |
|  | | component +-+-+------
|  | +-----------+ | |
|  |               | |
|  +---------------+ |
|                    |
|  +---------------+ |
|  | assembly      | |
|  |               | |
|  | +-----------+ | |
|  | | component +-+-+-----
|  | +-----------+ | |
|  |               | |
|  | +-----------+ | |
|  | | component +-+-+-----
|  | +-----------+ | |
|  |               | |
|  | +-----------+ | |
|  | | component +-+-+----
|  | +-----------+ | |
|  |               | |
|  +---------------+ |
|                    |
+--------------------+


versus


             +------------------+
             |      component   |
             |                  |
      +------+--------+         |
      |  subcomponent |         |
      |               |         |
+-----+--------+      |         |
| subcomponent |      |         |
+-----+--------+      |         |
      |               |         |
+-----+--------+      |         |
| subcomponent |      |         |
+-----+--------+      |         |
      |               |         |
+-----+--------+      |         |
| subcomponent |      |         |
+-----+--------+      |         |
      |               |         |
      +------+--------+         |
             |                  |
      +------+--------+         |
      |  subcomponent |         |
      |               |         |
+-----+--------+      |         |
| subcomponent |      |         |
+-----+--------+      |         |
      |               |         |
+-----+--------+      |         |
| subcomponent |      |         |
+-----+--------+      |         |
      |               |         |
+-----+--------+      |         |
| subcomponent |      |         |
+-----+--------+      |         |
      |               |         |
      +------+--------+         |
             |                  |
             +------------------+




