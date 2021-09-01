from cx_Freeze import Executable
from cx_Freeze import setup

if __name__ == '__main__':
    options = {
        'build_exe': {
            'optimize': 1,
            'excludes': ['email', 'html', 'http', 'tkinter', 'unittest']
        }
    }

    executables = [
        Executable(script=r'ECO2\cli.py', target_name='ECO2'),
    ]

    setup(name='ECO2',
          version='0.1',
          description='ECO2',
          options=options,
          executables=executables)
