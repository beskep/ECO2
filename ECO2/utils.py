from logging import LogRecord
from os import PathLike

from loguru import logger
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import track as _track
from rich.theme import Theme


class _Handler(RichHandler):
    LVLS = {
        'TRACE': 5,
        'DEBUG': 10,
        'INFO': 20,
        'SUCCESS': 25,
        'WARNING': 30,
        'ERROR': 40,
        'CRITICAL': 50,
    }
    BLANK_NO = 21
    _NEW_LVLS = {5: 'TRACE', 25: 'SUCCESS', BLANK_NO: ''}

    def emit(self, record: LogRecord) -> None:
        if record.levelno in self._NEW_LVLS:
            record.levelname = self._NEW_LVLS[record.levelno]

        return super().emit(record)


StrPath = str | PathLike
console = Console(theme=Theme({'logging.level.success': 'blue'}))
_handler = _Handler(console=console, markup=True, log_time_format='[%X]')


def set_logger(level: int | str = 20):
    if isinstance(level, str):
        try:
            level = _Handler.LVLS[level.upper()]
        except KeyError as e:
            msg = f'`{level}` not in {list(_Handler.LVLS.keys())}'
            raise KeyError(msg) from e

    logger.remove()
    logger.add(
        _handler, level=level, format='{message}', backtrace=False, enqueue=True
    )
    logger.add(
        'eco2.log',
        level='DEBUG',
        rotation='1 month',
        retention='1 year',
        encoding='UTF-8-SIG',
        enqueue=True,
    )

    try:
        logger.level('BLANK')
    except ValueError:
        # 빈 칸 표시하는 'BLANK' level 새로 등록
        logger.level(name='BLANK', no=_Handler.BLANK_NO)


def track(
    sequence,
    description='Working...',
    total: float | None = None,
    **kwargs,
):
    """Track progress on console by iterating over a sequence."""
    return _track(
        sequence=sequence,
        description=description,
        total=total,
        console=console,
        **kwargs,
    )
