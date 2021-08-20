import click

from eco2 import Eco2


@click.group()
def cli():
    pass


@cli.command()
@click.argument('eco')
@click.option('-s',
              '--savedir',
              help=('해석한 header와 value 파일의 저장 경로. '
                    '미설정 시 eco 파일과 동일 경로에 저장.'))
@click.option('-h',
              '--header',
              default='header',
              help='header 파일 이름. 미설정 시 `header`로 지정.')
@click.option('-v',
              '--value',
              help=('value 파일 이름. '
                    '미설정 시 eco 파일과 동일 이름으로 저장.'))
def decrypt(eco, savedir, header, value):
    """
    \b
    eco 파일을 해석해서 header와 value 파일로 나눠 저장.
        header: eco의 버전, 생성 날짜 등 정보를 담은 바이너리 파일.
        value : 해석 설정 정보를 담은 xml 파일.

    \b
    Argument:
        ECO: 해석할 eco 파일 경로
    """
    Eco2.decrypt(path=eco,
                 save_dir=savedir,
                 header_name=header,
                 value_name=value)


@cli.command()
@click.argument('header')
@click.argument('value')
@click.option('-s',
              '--savedir',
              help=('해석한 header와 value 파일의 저장 경로. '
                    '미설정 시 value 파일과 동일 경로에 저장.'))
def encrypt(header, value, savedir):
    """
    header와 value를 암호화해서 eco 파일로 변환

    \b
    Arguments:
        HEADER: header 파일 경로.
        VALUE : value 파일 경로. 폴더 경로를 지정하면 해당 폴더에 존재하는 모든 .xml 파일을 변환.
    """
    Eco2.encrypt_dir(header_path=header, value_path=value, save_dir=savedir)


if __name__ == '__main__':
    cli()
