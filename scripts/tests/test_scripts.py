"""Exercise wrappers and destructive-path guards in disposable workspaces."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]


class ScriptsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ros tooling ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'workspace with spaces'
        shutil.copytree(SCRIPTS, self.root / 'scripts')
        (self.root / 'src').mkdir()
        (self.root / 'AGENTS.md').touch()
        # Isolate wrapper behavior from the host ROS installation.
        (self.root / 'scripts/env.sh').write_text('export TOOLING_ENV_LOADED=yes\n')
        self.bin = Path(self.temp.name) / 'bin'
        self.bin.mkdir()
        colcon = self.bin / 'colcon'
        colcon.write_text('''#!/usr/bin/env python3
import json, os, sys
with open(os.environ['CALLS'], 'a') as output:
    output.write(json.dumps([os.getcwd(), os.environ.get('TOOLING_ENV_LOADED'), sys.argv[1:]]) + '\\n')
sys.exit(int(os.environ.get('RESULT_STATUS' if sys.argv[1] == 'test-result' else 'RUN_STATUS', '0')))
''')
        colcon.chmod(0o755)
        self.calls = Path(self.temp.name) / 'calls.jsonl'
        self.env = dict(os.environ, PATH=f'{self.bin}:{os.environ["PATH"]}', CALLS=str(self.calls))

    def run_script(self, name, *args):
        return subprocess.run(['bash', str(self.root / 'scripts' / name), *args],
                              cwd='/tmp', env=self.env, capture_output=True, text=True)

    def recorded(self):
        return [json.loads(line) for line in self.calls.read_text().splitlines()]

    def test_build_preserves_arguments_and_failure(self):
        self.env['RUN_STATUS'] = '7'
        args = ['--packages-select', 'robot_diagnostics', '--cmake-args', '-DVALUE=a b']
        self.assertEqual(self.run_script('build.sh', *args).returncode, 7)
        self.assertEqual(self.recorded(), [[str(self.root), 'yes', ['build', '--symlink-install', *args]]])

    def test_test_checks_results_after_command_failure(self):
        self.env['RUN_STATUS'] = '8'
        args = ['--packages-select', 'robot_diagnostics', '--pytest-args', '-k', 'a or b']
        self.assertEqual(self.run_script('test.sh', *args).returncode, 8)
        calls = self.recorded()
        self.assertEqual(calls[0][2], ['test', '--return-code-on-test-failure', *args])
        self.assertEqual(calls[1][2], ['test-result', '--all', '--verbose'])

    def test_result_failure_is_reported(self):
        self.env['RESULT_STATUS'] = '1'
        self.assertEqual(self.run_script('test.sh').returncode, 1)

    def test_success(self):
        self.assertEqual(self.run_script('build.sh').returncode, 0)
        self.assertEqual(self.run_script('test.sh').returncode, 0)

    def test_environment_failure_stops_colcon(self):
        (self.root / 'scripts/env.sh').write_text('return 9\n')
        for name in ['build.sh', 'test.sh']:
            self.assertNotEqual(self.run_script(name).returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_source_environment_preserves_shell_and_loads_overlay(self):
        setup = Path(self.temp.name) / 'ros-setup.bash'
        setup.write_text('export TOOLING_ROS_LOADED=yes\n')
        # Substitute only the fixed ROS setup path, exercising the real env logic.
        env_script = self.root / 'scripts/env.sh'
        env_script.write_text((SCRIPTS / 'env.sh').read_text().replace(
            '/opt/ros/lyrical/setup.bash', str(setup)))
        command = '''before=$-; original=$PWD
source "$1" || exit $?
[[ "$before" == "$-" && "$original" == "$PWD" && "$TOOLING_ROS_LOADED" == yes ]]
'''
        def source_env():
            return subprocess.run(['bash', '-c', command, 'bash', str(env_script)],
                                  cwd='/tmp', capture_output=True, text=True)
        result = source_env()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('not built yet', result.stderr)
        (self.root / 'install').mkdir()
        (self.root / 'install/setup.bash').write_text('printf "overlay loaded\\n"\n')
        result = source_env()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('overlay loaded', result.stdout)
        (self.root / 'install/setup.bash').write_text('return 3\n')
        self.assertNotEqual(source_env().returncode, 0)
        setup.unlink()
        result = source_env()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('setup is missing', result.stderr)

    def test_clean_requires_explicit_yes(self):
        for name in ['build', 'install', 'log']:
            (self.root / name).mkdir()
            (self.root / name / 'marker').touch()
        for args in [(), ('',), ('--force',)]:
            result = self.run_script('clean.sh', *args)
            self.assertEqual(result.returncode, 2 if args == ('--force',) else 0)
            self.assertTrue((self.root / 'build/marker').exists())
        self.assertEqual(self.run_script('clean.sh', '--yes').returncode, 0)
        self.assertTrue((self.root / 'src').is_dir())
        for name in ['build', 'install', 'log']:
            self.assertFalse((self.root / name).exists())

    def test_clean_rejects_links_before_any_deletion(self):
        (self.root / 'build').mkdir()
        for target in [self.root, Path(self.temp.name), self.root / 'missing']:
            with self.subTest(target=target):
                (self.root / 'log').symlink_to(target, target_is_directory=True)
                self.assertNotEqual(self.run_script('clean.sh', '--yes').returncode, 0)
                self.assertTrue((self.root / 'build').is_dir())
                (self.root / 'log').unlink()

    def test_clean_rejects_file_and_invalid_workspace(self):
        (self.root / 'install').touch()
        self.assertNotEqual(self.run_script('clean.sh', '--yes').returncode, 0)
        (self.root / 'install').unlink()
        (self.root / 'AGENTS.md').unlink()
        self.assertNotEqual(self.run_script('clean.sh', '--yes').returncode, 0)


if __name__ == '__main__':
    unittest.main()
