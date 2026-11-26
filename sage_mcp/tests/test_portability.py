"""Portability regressions exercised on any host; native Windows still needs a smoke run."""
import ctypes
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PureWindowsPath
from unittest.mock import Mock, patch

from sage_mcp import runner
from sage_mcp.repo import tools_dir
sys.path.insert(0,str(tools_dir()))
import validate
import yamlmini


class Portability(unittest.TestCase):
    def test_windows_public_substitute_key(self):
        f=Mock(); f.exists.return_value=True; f.is_dir.return_value=False
        f.resolve.return_value.relative_to.return_value=PureWindowsPath('records/pinned.json')
        errs=[]; stats={'refs':0}
        ref={'path':'records/pinned.json','sha256':'a'*64,'storage_class':'public'}
        with patch.object(validate.op,'expand',return_value=f), patch.object(validate.op,'sha256_file',return_value='b'*64), \
             patch.object(validate,'public_copies',return_value={'records/pinned.json':('a'*64,'b'*64)}), \
             patch.object(validate,'frozen_version',return_value=None):
            validate.check_refs({'file':ref},'fixture',errs,[],stats)
        self.assertEqual(errs,[])
        self.assertEqual(stats['public_copy'],1)

    def test_windows_pid_uses_query_not_signal(self):
        with patch.object(runner.os,'name','nt'), patch.object(runner,'_windows_pid_alive',return_value=True) as query, \
             patch.object(runner.os,'kill') as signal:
            self.assertTrue(runner.pid_alive(123456789))
            query.assert_called_once_with(123456789)
            signal.assert_not_called()

    def test_windows_process_handle_closed(self):
        kernel=Mock(); kernel.OpenProcess.return_value=42
        with patch.object(ctypes,'WinDLL',return_value=kernel,create=True):
            for result,alive in ((258,True),(0,False)):
                kernel.WaitForSingleObject.return_value=result
                self.assertEqual(runner._windows_pid_alive(123),alive)
        self.assertEqual(kernel.CloseHandle.call_count,2)

    def test_windows_invalid_pid_is_gone(self):
        kernel=Mock();kernel.OpenProcess.return_value=0
        with patch.object(ctypes,'WinDLL',return_value=kernel,create=True), \
             patch.object(ctypes,'get_last_error',return_value=87,create=True):
            self.assertFalse(runner._windows_pid_alive(123))
        kernel.CloseHandle.assert_not_called()

    def test_unicode_reads_under_ascii_default(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'utf8.yaml';p.write_bytes('title: Arróyave ΔG\n'.encode('utf-8'))
            original=Path.read_text
            def legacy_read(path,*args,**kwargs):
                kwargs.setdefault('encoding','ascii')
                return original(path,*args,**kwargs)
            with patch.object(Path,'read_text',legacy_read):
                self.assertEqual(yamlmini.load(p)['title'],'Arróyave ΔG')
                self.assertEqual(runner.tail(p),'title: Arróyave ΔG')

    def test_git_preserves_pinned_line_endings(self):
        repo=Path(__file__).resolve().parents[2]
        result=subprocess.run(['git','check-attr','text','--','protocols/general/orchid-calphad-fit@2.1.2.yaml',
                               'assessments/crni-paper-fit-step4-s1/evidence/states.json'],cwd=repo,capture_output=True,text=True,check=True)
        self.assertEqual(result.stdout.count(': text: unset'),2)
