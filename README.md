In order to use PyDL you will need to add to the python path so
that the files can be located

put something like the following in your ~/.bashrc or ~/.bash_profile:
 export PYTHONPATH=$PYTHONPATH:<path to where you downloaded PyDL>
don't include /PyDL at the end, so that you can in Python do
 from PyDL import *

Packages you need to install for this to work:
Ubuntu apt packages:
 apt install graphviz libgraphviz-dev

Python3 packages:
 python3 -m pip install pygraphviz commentjson orjson numexpr matplotlib


tests folder includes some tests to verify functionality of PyDL
