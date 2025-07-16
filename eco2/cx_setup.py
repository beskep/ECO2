from __future__ import annotations

import sysconfig
import tomllib
from pathlib import Path

from cx_Freeze import Executable, setup

if __name__ == '__main__':
    path = Path(__file__).parents[1] / 'pyproject.toml'
    pyprj = tomllib.loads(path.read_text())
    project = pyprj['project']['name']
    version = pyprj['project']['version']

    platform = sysconfig.get_platform()
    pyver = sysconfig.get_python_version()

    options = {
        'build_exe': {
            'build_exe': f'build/{project}-{version}-{platform}-py{pyver}',
            'optimize': 1,
            'excludes': ['email', 'http', 'pytest', 'tkinter', 'unittest'],
            'include_files': 'bin',
        }
    }

    executables = [
        Executable(script=r'eco2\cli.py', target_name='eco2'),
    ]

    setup(
        options=options,
        executables=executables,
    )
