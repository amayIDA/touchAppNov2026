import tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
import touchscreen_launcher as launcher

class BootstrapTests(unittest.TestCase):
 def test_ready_runtime_does_not_install(self):
  with tempfile.TemporaryDirectory() as folder, patch.object(launcher,'ROOT',Path(folder)):
   python=Path(folder)/'.touchscreen-env/Scripts/python.exe'
   with patch.object(launcher,'find_python',return_value=python),patch.object(launcher,'valid_python',return_value=python),patch.object(launcher,'install_python') as install,patch.object(launcher,'run',return_value=Mock(returncode=0)) as run:
    self.assertEqual(launcher.ensure_runtime(),python);install.assert_not_called();self.assertEqual(run.call_count,1)
 def test_missing_packages_install_and_recheck(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(launcher,'ROOT',Path(folder)):
   python=Path(folder)/'.touchscreen-env/Scripts/python.exe'
   with patch.object(launcher,'find_python',return_value=python),patch.object(launcher,'valid_python',return_value=python),patch.object(launcher,'run',side_effect=[Mock(returncode=1),Mock(returncode=0),Mock(returncode=0)]) as run:
    self.assertEqual(launcher.ensure_runtime(),python)
    args=run.call_args_list[1].args[0];self.assertIn('pip',args);self.assertIn('https://pypi.org/simple',args);self.assertEqual(run.call_count,3)
 def test_install_failure_stops_launch(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(launcher,'ROOT',Path(folder)):
   python=Path(folder)/'.touchscreen-env/Scripts/python.exe'
   with patch.object(launcher,'find_python',return_value=python),patch.object(launcher,'valid_python',return_value=python),patch.object(launcher,'run',side_effect=[Mock(returncode=1),Mock(returncode=1)]):
    with self.assertRaisesRegex(RuntimeError,'Dependency installation failed'):launcher.ensure_runtime()

if __name__=='__main__':unittest.main()
