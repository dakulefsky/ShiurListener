"""Bound GUI test hangs in CI and print thread stacks instead of waiting indefinitely."""
import faulthandler,pathlib,sys,unittest
if __name__=='__main__':
 faulthandler.enable()
 faulthandler.dump_traceback_later(90,exit=True)
 pattern=sys.argv[1] if len(sys.argv)>1 else 'test*.py'
 suite=unittest.defaultTestLoader.discover(str(pathlib.Path(__file__).parent),pattern=pattern)
 class ImmediateResult(unittest.TextTestResult):
  def addFailure(self,test,error):
   super().addFailure(test,error);self.stream.write(self._exc_info_to_string(error,test))
  def addError(self,test,error):
   super().addError(test,error);self.stream.write(self._exc_info_to_string(error,test))
 result=unittest.TextTestRunner(verbosity=2,resultclass=ImmediateResult).run(suite)
 faulthandler.cancel_dump_traceback_later()
 sys.exit(0 if result.wasSuccessful() else 1)
