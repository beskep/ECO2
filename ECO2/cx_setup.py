import sysconfig
from pathlib import Path

import rtoml
from cx_Freeze import Executable, setup

if __name__ == '__main__':
    pyprj = rtoml.load(Path(__file__).parents[1] / 'pyproject.toml')
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
        Executable(script=r'ECO2\cli.py', target_name='ECO2'),
    ]

    setup(
        options=options,
        executables=executables,
    )
