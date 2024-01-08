from cx_Freeze import Executable, setup

if __name__ == '__main__':
    excludes = ['email', 'http', 'pytest', 'tkinter', 'unittest']
    options = {
        'build_exe': {
            'optimize': 1,
            'excludes': excludes,
        }
    }

    executables = [
        Executable(script=r'ECO2\cli.py', target_name='ECO2'),
    ]

    setup(
        options=options,
        executables=executables,
    )
