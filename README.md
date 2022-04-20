# PyDL - Python AHP Graph
In order to use PyDL you will need to add to the python path so
that the files can be located

put something like the following in your ~/.bashrc or ~/.bash_profile:
```Bash
export PYTHONPATH=$PYTHONPATH:<path to where you downloaded PyDL>
```
don't include /PyDL at the end, so that you can in Python do
```Python
from PyDL import *
```
### Ubuntu apt packages:
```Bash
apt install graphviz libgraphviz-dev
```
### Python3 packages:
```Bash
python3 -m pip install pygraphviz orjson
```
