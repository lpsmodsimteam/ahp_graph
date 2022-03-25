"""
Fake Components if SST cannot be include (ie. running in python3).

This module defines portions of the Component and Link classes
in the SST Python interface so we can generate PyDL models outside
of SST.  This module is only loaded if the standard SST import fails.
"""


class Component(object):
    """An SST component."""

    def __init__(self, name: str, objref) -> 'Component':
        """Initialize the component name and reference."""
        self._name = name
        self._objref = objref
        print(f"Component '{name}' of class '{objref}'")

    def addParams(self, params: dict) -> None:
        """Add parameters to a component."""
        self.params = params
        for (key, val) in self.params.items():
            print(f"    {self._name}:{key} = '{val}'")


class Link(object):
    """A link between two SST components."""

    def __init__(self, name: str) -> 'Link':
        """Initialize a link with a name."""
        self._name = name

    def connect(self, A: 'Component', B: 'Component') -> None:
        """Connect components A and B together on this link."""
        self.c0 = A[0]
        self.p0 = A[1]
        self.t0 = A[2]
        self.c1 = B[0]
        self.p1 = B[1]
        self.t1 = B[2]
        print(f"Link '{self._name}'")
        print(f"    {self.c0._name}:{self.p0}")
        print(f"    {self.c1._name}:{self.p1}")
