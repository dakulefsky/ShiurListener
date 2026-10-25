"""Bound GUI test hangs in CI and print thread stacks instead of waiting indefinitely."""
import faulthandler,pathlib,sys,unittest
if __name__=='__main__':
 faulthandler.enable()
 faulthandler.dump_traceback_later(90,exit=True)
 suite=unittest.defaultTestLoader.discover(str(pathlib.Path(__file__).parent))
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 faulthandler.cancel_dump_traceback_later()
 sys.exit(0 if result.wasSuccessful() else 1)
