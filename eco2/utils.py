# ruff: noqa: D103
from __future__ import annotations

import logging
import logging.handlers
from typing import TYPE_CHECKING

import structlog
from rich import progress
from rich.highlighter import RegexHighlighter
from rich.logging import RichHandler
from rich.text import Text

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from rich.highlighter import Highlighter
    from rich.style import Style
    from rich.table import Column
    from structlog.typing import EventDict, WrappedLogger


class _ConsoleRenderer(structlog.dev.ConsoleRenderer):
    DROP = (
        'timestamp',
        'level',
        'filename',
        'lineno',
        'func_name',
        '_record',
        '_from_structlog',
    )

    def __call__(self, logger: WrappedLogger, name: str, event_dict: EventDict) -> str:
        for key in self.DROP:
            event_dict.pop(key, None)

        return super().__call__(logger, name, event_dict)


def setup_logger(level: int = 20, file: str = 'eco2.log') -> None:
    shared: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.PositionalArgumentsFormatter(),
    ]

    rich_handler = RichHandler(log_time_format='%X')
    rich_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=_ConsoleRenderer(colors=False, sort_keys=False),
            foreign_pre_chain=shared,
        )
    )

    file_handler = logging.handlers.TimedRotatingFileHandler(
        file, when='d', interval=30
    )
    file_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(ensure_ascii=False),
            foreign_pre_chain=shared,
        )
    )

    logging.basicConfig(
        level=level,
        handlers=[rich_handler, file_handler],
    )

    structlog.configure(
        processors=[
            *shared,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.dev.set_exc_info,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.TimeStamper(fmt='%Y-%m-%d %H:%M:%S'),
            structlog.processors.CallsiteParameterAdder([
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


class _ProgressHighlighter(RegexHighlighter):
    highlights = [r'(?P<dim>\d+/\d+=0*)(\d*%)']  # noqa: RUF012


class _ProgressColumn(progress.TaskProgressColumn):
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
            highlighter=highlighter or _ProgressHighlighter(),
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


def track[T](
    sequence: Sequence[T] | Iterable[T],
    *,
    description: str = 'Working...',
    total: float | None = None,
    completed: int = 0,
    transient: bool = False,
) -> Iterable[T]:
    with progress.Progress(
        progress.TextColumn('[progress.description]{task.description}'),
        progress.BarColumn(bar_width=60),
        _ProgressColumn(show_speed=True),
        progress.TimeRemainingColumn(compact=True, elapsed_when_finished=True),
        transient=transient,
    ) as p:
        yield from p.track(
            sequence,
            total=total,
            completed=completed,
            description=description,
        )


if __name__ == '__main__':
    setup_logger(10)

    logger = structlog.stdlib.get_logger(__name__)

    for lvl in track(list(range(10, 60, 10))):
        logger.log(lvl, 'log', lvl=lvl, answer=42)
