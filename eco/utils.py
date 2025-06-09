from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

import rich
from loguru import logger
from rich import progress
from rich.highlighter import RegexHighlighter
from rich.logging import RichHandler
from rich.text import Text
from rich.theme import Theme

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from logging import LogRecord

    from rich.highlighter import Highlighter
    from rich.style import Style
    from rich.table import Column


console = rich.get_console()
console.push_theme(Theme({'logging.level.success': 'bold blue'}))


class LogHandler(RichHandler):
    _NEW_LEVELS: ClassVar[dict[int, str]] = {5: 'TRACE', 25: 'SUCCESS'}

    def emit(self, record: LogRecord) -> None:
        if name := self._NEW_LEVELS.get(record.levelno):
            record.levelname = name

        return super().emit(record)

    @classmethod
    def set(
        cls,
        level: int | str = 20,
        *,
        rich_tracebacks: bool = False,
        remove: bool = True,
        **kwargs: Any,
    ) -> None:
        """
        `loguru.logger` 세팅.

        Parameters
        ----------
        level : int | str, optional
        rich_tracebacks : bool, optional
        remove : bool, optional

        Examples
        --------
        >>> LogHandler.set(20)
        >>> from loguru import logger
        >>> logger.debug('debug')
        >>> logger.info('info')  # doctest: +ELLIPSIS
        [...] INFO ...
        >>> logger.success('success')  # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
              SUCCESS ...
        """
        handler = cls(
            console=console,
            markup=True,
            log_time_format='[%X]',
            rich_tracebacks=rich_tracebacks,
        )

        if remove:
            logger.remove()

        logger.add(handler, level=level, format='{message}', **kwargs)


class ProgressHighlighter(RegexHighlighter):
    highlights = [r'(?P<dim>\d+/\d+=0*)(\d*%)']  # noqa: RUF012


class ProgressColumn(progress.TaskProgressColumn):
    def __init__(
        self,
        *,
        style: str | Style = 'progress.download',
        highlighter: Highlighter | None = None,
        table_column: Column | None = None,
        show_speed: bool = False,
    ) -> None:
        super().__init__(
            text_format='',
            text_format_no_percentage='',
            style=style,
            justify='left',
            markup=True,
            highlighter=highlighter or ProgressHighlighter(),
            table_column=table_column,
            show_speed=show_speed,
        )

    @staticmethod
    def text(task: progress.Task) -> str:
        completed = int(task.completed)
        total = int(task.total) if task.total is not None else '?'
        width = len(str(total))
        return f'{completed:{width}d}/{total}={task.percentage:>03.0f}%'

    def render(self, task: progress.Task) -> Text:
        if task.total is None and self.show_speed:
            return self.render_speed(task.finished_speed or task.speed)

        s = self.text(task=task)
        text = Text(s, style=self.style, justify=self.justify)

        if self.highlighter:
            self.highlighter.highlight(text)

        return text


class Progress(progress.Progress):
    @classmethod
    def get_default_columns(cls) -> tuple[progress.ProgressColumn, ...]:
        return (
            progress.TextColumn('[progress.description]{task.description}'),
            progress.BarColumn(bar_width=60),
            ProgressColumn(show_speed=True),
            progress.TimeRemainingColumn(compact=True, elapsed_when_finished=True),
        )

    @classmethod
    def iter[T](
        cls,
        sequence: Sequence[T] | Iterable[T],
        *,
        description: str = 'Working...',
        total: float | None = None,
        completed: int = 0,
        transient: bool = False,
    ) -> Iterable[T]:
        """
        Trace progress.

        Yields
        ------
        T

        Examples
        --------
        >>> for _ in Progress.iter(range(10)):  # doctest: +ELLIPSIS
        ...     pass
        Working... ...
        >>> def it(x):
        ...     yield from x
        >>> for _ in Progress.iter(it(range(10)), description='Iterating...'):
        ...     pass
        Iterating... ...
        """
        with cls(transient=transient) as p:
            yield from p.track(
                sequence,
                total=total,
                completed=completed,
                description=description,
            )


if __name__ == '__main__':
    import time

    for _ in Progress.iter(list(range(100))):
        time.sleep(0.01)

    LogHandler.set(1, rich_tracebacks=False)

    logger.trace('Trace')
    logger.debug('Debug')
    logger.info('Info')
    logger.success('Success')
    logger.warning('Warning')
    logger.error('Error')
    logger.critical('Critical')

    try:
        x = 1 / 0
    except ZeroDivisionError as e:
        logger.exception(repr(e))
