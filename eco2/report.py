"""ECO2 계산 결과 해석."""

from __future__ import annotations

import contextlib
import dataclasses as dc
import functools
import io
from itertools import chain
from typing import IO, TYPE_CHECKING

import polars as pl
import polars.selectors as cs

if TYPE_CHECKING:
    from pathlib import Path


def _key_value(data: str) -> tuple[None, float] | tuple[str, None]:
    try:
        return (None, float(data))
    except ValueError:
        return (data.rstrip(' :'), None)


class ReportError(ValueError):  # noqa: D101
    pass


class ReportFormatError(ReportError):  # noqa: D101
    pass


class EmptyDataError(ReportError):  # noqa: D101
    pass


@dc.dataclass(frozen=True)
class BaseReport:
    """Abstract class."""

    source: str | Path | IO[bytes] | bytes

    @functools.cached_property
    def raw(self) -> pl.DataFrame:
        """엑셀 원본."""
        with contextlib.redirect_stderr(io.StringIO()):
            return pl.read_excel(self.source)

    @functools.cached_property
    def data(self) -> pl.DataFrame:
        """추출, 가공한 데이터."""
        raise NotImplementedError


@dc.dataclass(frozen=True)
class GraphReportRows:
    """`그래프 > 계산결과그래프` 엑셀 row 정보."""

    monthly: tuple[int, int] = (0, 2)
    yearly: tuple[int, int] = (2, 8)
    stats: int = -3


@dc.dataclass(frozen=True)
class GraphReport(BaseReport):
    """`그래프 > 계산결과그래프` 파일."""

    rows: GraphReportRows = dc.field(default_factory=GraphReportRows)

    @functools.cached_property
    def raw(self) -> pl.DataFrame:
        """엑셀 원본."""
        raw = super().raw

        if 'No Data' in raw:
            raise EmptyDataError(self.source)

        if '에너지자립률(전체):' not in raw[:, 0].str.strip_chars():
            raise ReportFormatError(self.source)

        return raw

    @functools.cached_property
    def stats(self) -> dict[str, float]:
        """
        결과 그래프 마지막 2줄 정보.

        자립률, 단위면적당 1차에너지 생산량·소비량.
        """
        tail = self.raw[self.rows.stats :]
        stats = tail.select([
            s.name
            for s in tail
            if not s.is_null().all() and '％' not in s  # noqa: RUF001
        ])

        kv = [_key_value(x) for x in chain.from_iterable(stats.iter_rows()) if x]
        keys = (k for k, _ in kv if k is not None)
        values = (v for _, v in kv if v is not None)

        return dict(zip(keys, values, strict=True))

    @property
    def building_type(self) -> str:
        """주거/비주거."""
        return self._monthly[0]

    @property
    def monthly(self) -> pl.DataFrame:
        """월간 정보."""
        return self._monthly[1]

    @functools.cached_property
    def _monthly(self) -> tuple[str, pl.DataFrame]:
        r = self.rows.monthly
        df = self.raw.drop(cs.contains('UNNAMED'))[r[0] : r[1]]

        if (width := df.width) != 13:  # noqa: PLR2004
            msg = f'{width=} != 13'
            raise AssertionError(msg)

        building_type = df.columns[0]
        monthly = (
            df.rename({building_type: 'energy'})
            .with_columns(pl.all().exclude('energy').cast(pl.Float64))
            .unpivot(index='energy', variable_name='month')
            .with_columns(
                pl.col('month').str.strip_suffix('월').cast(pl.Int8),
                pl.lit('kWh/m²').alias('unit'),
            )
            .sort('energy', 'month')
        )

        return building_type, monthly

    @functools.cached_property
    def yearly(self) -> pl.DataFrame:
        """연간 정보."""
        r = self.rows.yearly
        df = self.raw[r[0] + 1 : r[1]]

        null = [s.name for s in df if s.is_null().all()]
        columns = self.raw.drop(null).row(r[0])

        df = df.drop(null)
        df.columns = ['variable', *columns[1:]]

        return (
            df.with_columns(pl.all().exclude('variable').cast(pl.Float64))
            .unpivot(index='variable', variable_name='energy')
            .with_columns(
                pl.col('variable')
                .replace_strict('CO2발생량', 'kgCO₂/m²', default='kWh/m²yr')
                .alias('unit')
            )
            .sort('variable', 'energy')
        )

    def _stats(self) -> pl.DataFrame:
        return (
            pl.DataFrame(
                list(self.stats.items()),
                schema=[('variable', pl.String), ('value', pl.Float64)],
                orient='row',
            )
            .select(
                pl.lit('기타').alias('category'),
                pl.all(),
                pl.col('variable')
                .str.extract('^((단위면적당)|(에너지자립률)).*')
                .replace_strict({'단위면적당': 'kWh/m²yr', '에너지자립률': '%'})
                .alias('unit'),
            )
            .sort(pl.col('variable'))
        )

    @functools.cached_property
    def data(self) -> pl.DataFrame:
        """추출, 가공한 데이터."""
        monthly = self.monthly.select(
            pl.lit('월별').alias('category'),
            pl.lit('요구량').alias('variable'),
            pl.all(),
        )
        yearly = self.yearly.select(pl.lit('연간').alias('category'), pl.all())
        stats = self._stats()

        return pl.concat([monthly, yearly, stats], how='diagonal_relaxed')


@dc.dataclass(frozen=True)
class UploadReport(BaseReport):
    """`계산결과 > 업로드양식` 파일."""

    @functools.cached_property
    def raw(self) -> pl.DataFrame:
        """엑셀 원본."""
        raw = super().raw.with_columns(
            pl.col('단위')
            .replace({'-': None})
            .str.replace_many(['㎡', '년', '•'], ['m²', 'yr', ''])
        )

        if raw.columns[:3] != ['고시일', '구분코드', '구분']:
            raise ReportFormatError(self.source)

        if unnamed := raw.select(cs.contains('__UNNAMED__')).columns:
            raw = raw.rename({unnamed[0]: '값'})

        return raw

    @functools.cached_property
    def data(self) -> pl.DataFrame:
        """추출, 가공한 데이터."""
        m = (
            pl.col('값')
            .str.ends_with('%')
            .replace_strict({True: 0.01, False: 1.0}, return_dtype=pl.Float64)
        )
        return (
            (self.raw)
            .with_columns(
                pl.col('값')
                .str.replace_all(',', '')
                .str.strip_suffix('%')
                .cast(pl.Float64, strict=False)
                .alias('value')
            )
            .with_columns((pl.col('value') * m).alias('value'))
        )


@dc.dataclass(frozen=True)
class CalculationsReport(BaseReport):
    """`계산결과 > 계산결과` 파일."""

    header_row: int = 4

    @functools.cached_property
    def raw(self) -> pl.DataFrame:
        """엑셀 원본."""
        with contextlib.redirect_stderr(io.StringIO()):
            r = pl.read_excel(self.source, read_options={'n_rows': 1})
            if r.columns[0] != '에너지 요구량 및 소요량':
                raise ReportFormatError(self.source)

            return pl.read_excel(
                self.source, read_options={'header_row': self.header_row}
            )

    @functools.cached_property
    def data(self) -> pl.DataFrame:
        """추출, 가공한 데이터."""
        return (
            self.raw.with_row_index()
            .rename({'에너지요구량': '변수', '[단위]': '단위', '[기호]': '기호&계수'})
            .with_columns(
                pl.when((pl.col('index') == 0) | (pl.col('합계') == '합계'))
                .then(pl.col('변수'))
                .otherwise(pl.lit(None))
                .alias('구분')
            )
            .with_columns(pl.col('구분').forward_fill())
            .drop(cs.contains('__UNNAMED__'))
            .select('index', '구분', pl.all().exclude('index', '구분'))
            .filter(pl.col('합계') != '합계')
            .with_columns(cs.ends_with('합계', '월').cast(pl.Float64))
        )
