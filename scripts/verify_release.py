#!/usr/bin/env python3
"""Run RC1 tests in a portable way with compiler/runtime on PYTHONPATH."""
import pathlib, subprocess, sys, os
root=pathlib.Path(__file__).resolve().parents[1]
rc1=root/'rc1/Chapter4_Compiler_Release_Candidate_RC1'
env=os.environ.copy()
env['PYTHONPATH']=str(rc1)+os.pathsep+env.get('PYTHONPATH','')
cmd=[sys.executable,'-m','unittest','discover','-s',str(rc1/'tests'),'-p','test_*.py']
raise SystemExit(subprocess.call(cmd,cwd=rc1,env=env))
