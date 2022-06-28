from cx_Freeze import Executable
from cx_Freeze import setup

if __name__ == '__main__':
    excludes = ['email', 'html', 'http', 'pytest', 'tkinter', 'unittest']
    options = {
        'build_exe': {
            'optimize': 1,
            'excludes': excludes,
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
