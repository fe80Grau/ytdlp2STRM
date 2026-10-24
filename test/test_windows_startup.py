"""Windows startup regression tests; never import/run the real application.

Run: python -m unittest discover -s test -p test_windows_startup.py -v
Only temporary fixture files are executed. No scheduled tasks are registered.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}


@unittest.skipUnless(sys.platform == "win32", "requires Windows cmd.exe")
class WindowsStartupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="startup spaces ", dir=os.environ.get("YTDLP2STRM_TEST_TMP")
        )
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "Project with spaces & symbols"
        self.project.mkdir()
        (self.project / "scripts").mkdir()
        launcher = ROOT / "scripts" / "start-windows.cmd"
        if launcher.exists():
            shutil.copy2(launcher, self.project / "scripts" / launcher.name)
        (self.project / "main.py").write_text(
            "import os, sys\n"
            "print('FIXTURE_STDOUT')\n"
            "print('CWD=' + os.getcwd())\n"
            "print('UNBUFFERED=' + str(sys.stdout.write_through))\n"
            "raise RuntimeError('FIXTURE_STARTUP_FAILURE')\n",
            encoding="utf-8",
        )

    def run_installer(self, *options, scheduler_stub=None):
        shell = shutil.which("powershell.exe")
        assert shell is not None
        script = ROOT / "scripts" / "install-windows-task.ps1"
        def literal(value):
            return "'" + str(value).replace("'", "''") + "'"
        # Even a regression must not register a real task during this suite.
        guard = ("function Register-ScheduledTask { throw 'TEST_REGISTRATION_FORBIDDEN' }; "
                 "function Get-ScheduledTask { throw 'TEST_SCHEDULER_ACCESS_FORBIDDEN' }; ")
        command = ("$ErrorActionPreference='Stop'; "
                   "[Console]::OutputEncoding = [Text.UTF8Encoding]::new(); "
                   + guard + (scheduler_stub or "") + "& " + literal(script)
                   + " -ProjectPath " + literal(self.project)
                   + " -PythonExe " + literal(sys.executable) + " " + " ".join(options))
        return subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-Command", command],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )

    def test_installer_refuses_to_replace_an_existing_task(self):
        result = self.run_installer(scheduler_stub=(
            "function Get-ScheduledTask { [pscustomobject]@{TaskName='ytdlp2STRM'} }; "
        ))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists", result.stderr)
        self.assertNotIn("TEST_REGISTRATION_FORBIDDEN", result.stderr)

    def test_installer_dry_run_outputs_xml_without_writing_files(self):
        before = sorted(str(p) for p in self.project.rglob("*"))
        for option in ("-DryRun", "-WhatIf"):
            with self.subTest(option=option):
                result = self.run_installer(option)
                self.assertEqual(result.returncode, 0, result.stderr)
                task = ET.fromstring(result.stdout.strip())
                action = task.find("t:Actions/t:Exec", NS)
                assert action is not None
                self.assertEqual(action.findtext("t:WorkingDirectory", namespaces=NS),
                                 str(self.project))
                arguments = action.findtext("t:Arguments", namespaces=NS)
                assert arguments is not None
                self.assertIn(sys.executable, arguments)
                self.assertIn(str(self.project / "scripts" / "start-windows.cmd"), arguments)
        self.assertEqual(before, sorted(str(p) for p in self.project.rglob("*")))
        self.assertFalse((self.project / "log.txt").exists())

    def test_launcher_uses_explicit_python_with_spaces_without_path(self):
        environment = Path(self.temp.name) / "Python with spaces"
        venv.EnvBuilder(with_pip=False).create(environment)
        python = environment / "Scripts" / "python.exe"
        (self.project / "main.py").write_text(
            "import sys\nprint('OUT')\nprint('ERR', file=sys.stderr)\nsys.exit(23)\n",
            encoding="utf-8",
        )
        launcher = self.project / "scripts" / "start-windows.cmd"
        env = dict(os.environ)
        env["PATH"] = os.path.join(os.environ["SystemRoot"], "System32")
        command = f'"{os.environ["COMSPEC"]}" /d /s /c ""{launcher}" "{python}""'
        for _ in range(2):
            result = subprocess.run(command, cwd=Path(self.temp.name), env=env,
                                    capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 23, result.stderr)
        log = (self.project / "log.txt").read_text(encoding="utf-8")
        self.assertEqual(log.count("Python exited with code 23"), 2)
        self.assertEqual(log.count("OUT"), 2)
        self.assertEqual(log.count("ERR"), 2)

    def test_launcher_logs_missing_interpreter(self):
        launcher = self.project / "scripts" / "start-windows.cmd"
        missing = self.project / "Missing Python" / "python.exe"
        command = f'"{os.environ["COMSPEC"]}" /d /s /c ""{launcher}" "{missing}""'
        result = subprocess.run(command, cwd=Path(self.temp.name),
                                capture_output=True, timeout=20)
        self.assertNotEqual(result.returncode, 0)
        log = (self.project / "log.txt").read_text(encoding="utf-8", errors="replace")
        self.assertIn(str(missing), log)
        self.assertIn("Python exited with code", log)
        self.assertNotIn("FIXTURE_STDOUT", log)

    def test_installer_xml_is_accepted_by_windows_task_parser(self):
        result = self.run_installer("-WhatIf")
        self.assertEqual(result.returncode, 0, result.stderr)
        task = ET.fromstring(result.stdout.strip())
        self.assertIsNotNone(task.find("t:Triggers/t:LogonTrigger", NS))
        self.assertIsNone(task.find("t:Triggers/t:BootTrigger", NS))
        self.assertEqual(task.findtext("t:Principals/t:Principal/t:LogonType", namespaces=NS),
                         "InteractiveToken")
        self.assertEqual(task.findtext("t:Principals/t:Principal/t:RunLevel", namespaces=NS),
                         "LeastPrivilege")
        xml_file = Path(self.temp.name) / "generated.xml"
        xml_file.write_text(result.stdout, encoding="utf-8")
        # NewTask only creates an in-memory definition: never RegisterTask.
        command = ("$ErrorActionPreference='Stop'; "
                   "$s=New-Object -ComObject Schedule.Service; $s.Connect(); "
                   "$d=$s.NewTask(0); $d.XmlText=[IO.File]::ReadAllText('"
                   + str(xml_file).replace("'", "''") + "'); 'XML_ACCEPTED'")
        parsed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True, text=True, errors="replace", timeout=20,
        )
        self.assertEqual(parsed.returncode, 0, parsed.stderr)
        self.assertIn("XML_ACCEPTED", parsed.stdout)
        action = task.find("t:Actions/t:Exec", NS)
        assert action is not None
        command = action.findtext("t:Command", namespaces=NS)
        arguments = action.findtext("t:Arguments", namespaces=NS)
        result = subprocess.run(f'"{command}" {arguments}', cwd=Path(self.temp.name),
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 1)
        log = (self.project / "log.txt").read_text(encoding="utf-8", errors="replace")
        self.assertIn("RuntimeError: FIXTURE_STARTUP_FAILURE", log)
        self.assertIn("UNBUFFERED=True", log)

    def test_installer_rejects_relative_paths(self):
        original = self.project
        self.project = Path("relative-project")
        try:
            result = self.run_installer("-WhatIf")
        finally:
            self.project = original
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("absolute local paths", result.stderr)

    def test_template_action_context_has_a_matching_principal(self):
        task = ET.parse(ROOT / "config" / "MS-TASK-ytdlp2STRM.xml")
        actions = task.find("t:Actions", NS)
        assert actions is not None
        context = actions.get("Context")
        if context:
            ids = [p.get("id") for p in task.findall("t:Principals/t:Principal", NS)]
            self.assertIn(context, ids)

    def test_template_captures_startup_exception_and_exit_code(self):
        task = ET.parse(ROOT / "config" / "MS-TASK-ytdlp2STRM.xml")
        action = task.find("t:Actions/t:Exec", NS)
        assert action is not None
        arguments = action.findtext("t:Arguments", namespaces=NS)
        assert arguments is not None
        arguments = arguments.replace(r"C:\ProgramData\ytdlp2STRM", str(self.project))
        arguments = arguments.replace(r"C:\Python311\python.exe", sys.executable)
        env = dict(os.environ)
        # Give the old template a real interpreter so RED isolates lost stderr.
        env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env["PATH"]
        result = subprocess.run(
            f'"{os.environ["COMSPEC"]}" {arguments}',
            cwd=self.project, env=env, capture_output=True, timeout=20,
        )
        log = (self.project / "log.txt").read_text(encoding="utf-8", errors="replace")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RuntimeError: FIXTURE_STARTUP_FAILURE", log)
        self.assertIn("FIXTURE_STDOUT", log)
        self.assertIn("CWD=" + str(self.project), log)
        self.assertIn("UNBUFFERED=True", log)


if __name__ == "__main__":
    unittest.main()
