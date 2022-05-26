import test.ber
import test.pdu.v2
import test.security
import test.security.levels
import test.security.usm.auth
import test.smi.v2
import test.types
import test.utils

# The order of this list is meant to test each module
# before testing the modules that depend on it
modules = [
    test.ber,
    test.types,
    test.utils,
    test.pdu.v2,
    test.smi.v2,
    test.security,
    test.security.levels,
    test.security.usm.auth,
]

def allTests(cls):
    for attrname in dir(cls):
        if attrname.startswith("test"):
            attr = getattr(cls, attrname)
            if hasattr(attr, "__call__"):
                yield cls(attrname)

import unittest
suite = unittest.TestSuite()
for module in modules:
    for name in module.__all__:
        suite.addTests(allTests(getattr(module, name)))

runner = unittest.TextTestRunner()
runner.run(suite)
