"""ECO2 저장 파일의 XML 정보 수정."""

from __future__ import annotations

import dataclasses as dc
import functools
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Self

import more_itertools as mi
from loguru import logger
from lxml import etree

from eco2 import core

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from lxml.etree import _Element

Level = Literal['debug', 'info', 'warning', 'error', 'raise']
SurfaceType = Literal[
    '외벽(벽체)',
    '외벽(지붕)',
    '외벽(바닥)',
    '내벽(벽체)',
    '내벽(지붕)',
    '내벽(바닥)',
    '간벽',
    '외부창',
    '내부창',
    '지중벽',
]

SURFACE_TYPE: tuple[SurfaceType, ...] = (
    '외벽(벽체)',
    '외벽(지붕)',
    '외벽(바닥)',
    '내벽(벽체)',
    '내벽(지붕)',
    '내벽(바닥)',
    '간벽',
    '외부창',
    '내부창',
    '지중벽',
)
CUSTOM_LAYER = """
<tbl_ykdetail>
  <pcode>0000</pcode>
  <code>0001</code>
  <설명>CustomMaterial</설명>
  <열전도율>0</열전도율>
  <두께>1000</두께>
  <구분>5</구분>
  <열저항>0</열저항>
  <전경색>-16776961</전경색>
  <후경색>-1</후경색>
  <커스텀>Y</커스텀>
</tbl_ykdetail>
"""


class EditorError(ValueError):  # noqa: D101
    pass


class ElementNotFoundError(EditorError):  # noqa: D101
    pass


def set_child_text(element: _Element, child: str, value: Any) -> None:  # noqa: ANN401
    """
    Element의 child 값 설정.

    Parameters
    ----------
    element : _Element
    child : str
    value : Any
    """
    c = mi.one(
        element.iterfind(child),
        too_short=ValueError(f'Child "{child}" not found in {element}'),
        too_long=ValueError(f'Child "{child}" found more than once in {element}'),
    )
    c.text = str(value)


@dc.dataclass(frozen=True)
class Area:
    """면적 정보."""

    site: float | None
    """대지면적"""

    building: float | None
    """건축면적"""

    floor: float | None
    """연면적"""

    raw: dict[str, str | None]

    KEY: ClassVar[dict[str, str]] = {
        'site': 'buildm21',
        'building': 'buildm22',
        'floor': 'buildm23',
    }

    @staticmethod
    def _value(element: _Element, path: str) -> float | None:
        if (text := element.findtext(path)) is None:
            raise ElementNotFoundError(element, path)

        try:
            return float(text.replace(',', ''))
        except ValueError:
            return None

    @classmethod
    def create(cls, desc: _Element) -> Self:
        """tbl_Desc로부터 생성."""
        return cls(
            **{k: cls._value(desc, p) for k, p in cls.KEY.items()},
            raw={k: desc.findtext(p) for k, p in cls.KEY.items()},
        )


# NOTE 개별 element 수정 기능은 Eco2Xml에,
# 전체 케이스 수정 기능은 Eco2Editor에 구현


@dc.dataclass
class Eco2Xml(core.Eco2Xml):
    """XML 개별 element 수정."""

    @functools.cached_property
    def area(self) -> Area:
        """대지·건축·연면적."""
        if (desc := self.ds.find('tbl_Desc')) is None:
            msg = 'tbl_Desc'
            raise ElementNotFoundError(msg)

        return Area.create(desc)

    def set_elements(
        self,
        path: str,
        value: str | None,
        *,
        edit_none: bool = False,
    ) -> None:
        """
        XML 내 모든 path의 값 수정.

        Parameters
        ----------
        path : str
        value : str | None
        edit_none : bool, optional
            기존 값이 지정되지 않았을 때 수정 여부.

        Examples
        --------
        침기율 1.0 설정
        >>> eco = Eco2Xml.create(src)  # doctest: +SKIP
        >>> eco = eco.set_element('tbl_zone/침기율', 1.0)  # doctest: +SKIP
        """
        for e in self.iterfind(path):
            if not edit_none and e.text is None:
                continue

            e.text = value

    def surfaces_by_type(self, t: int | SurfaceType, /) -> Generator[_Element]:
        """
        지정한 유형의 표면 순환.

        Parameters
        ----------
        t : int | SurfaceType

        Yields
        ------
        Generator[_Element]
        """
        if isinstance(t, str):
            t = SURFACE_TYPE.index(t)

        for e in self.iterfind('tbl_yk'):
            if int(e.findtext('면형태', -1)) == t:
                yield e

    def set_wall_uvalue(self, wall: _Element, uvalue: float) -> None:
        """
        벽체 u-value 설정.

        Parameters
        ----------
        wall : _Element
        uvalue : float
        """
        code = wall.findtext('code')
        assert code is not None

        # 기존 레이어 삭제
        for layer in self.iterfind('tbl_ykdetail'):
            if layer.findtext('pcode') == code:
                self.ds.remove(layer)

        # 새 레이어 추가
        layer = etree.fromstring(CUSTOM_LAYER)
        set_child_text(layer, 'pcode', code)
        set_child_text(layer, '열전도율', str(uvalue))
        set_child_text(layer, '열저항', f'{1 / uvalue:.4f}')

        last_layer = mi.last(self.iterfind('tbl_ykdetail'))
        index = self.ds.index(last_layer) + 1
        self.ds.insert(index, layer)

        # 벽체 열관류율 수정
        set_child_text(wall, '열관류율', uvalue)

    @staticmethod
    def set_window_uvalue(window: _Element, uvalue: float) -> None:
        """
        창 u-value 수정.

        Parameters
        ----------
        window : _Element
        uvalue : float
        """
        # 창호열관류율 수정
        set_child_text(window, '창호열관류율', uvalue)

        # 전체 열관류율 수정
        if balcony := float(window.findtext('발코니창호열관류율') or 0):
            t = 1.0 / (1.0 / uvalue + 1.0 / (2.0 * balcony))
            logger.debug('창호 전체 열관류율: {} (glazing={})', t, window)
            total = f'{t:.3f}'
        else:
            total = str(uvalue)

        set_child_text(window, '열관류율', total)

    def set_window_shgc(
        self,
        window: _Element,
        shgc: float,
        *,
        update_zero: bool = False,
    ) -> None:
        """
        창 SHGC 수정.

        Parameters
        ----------
        window : _Element
        shgc : float
        update_zero : bool, optional
            기존 SHGC가 0일 때 (문으로 추정) 수정 여부.
        """
        path = '일사에너지투과율'

        if not update_zero and (float(window.findtext(path) or 0) == 0):
            # '외부창'의 원래 SHGC가 0인 경우 (투과율 없는 문) 값을 수정하지 않음.
            return

        # 일사에너지투과율 수정
        set_child_text(window, path, shgc)

        # 전체 투과율 수정
        if balcony := float(window.findtext('발코니투과율') or 0):
            total = f'{balcony * shgc:.4f}' if balcony else str(shgc)
            set_child_text(window, '투과율', total)

            # tbl_myoun 투과율 수정
            pcode = window.findtext('code')
            assert pcode is not None
            for e in self.iterfind('tbl_myoun'):
                if e.findtext('열관류율2') == pcode:
                    set_child_text(e, '투과율', total)


class Eco2Editor:
    """ECO2 파일 수정."""

    def __init__(self, src: str | Path | core.Eco2) -> None:
        self.eco2 = src if isinstance(src, core.Eco2) else core.Eco2.read(src)
        self.xml = Eco2Xml.create(self.eco2)

    def write(self, path: str | Path, *, dsr: bool | None = False) -> None:
        """
        `.eco`, `.tpl` 파일 저장 (`.ecox`, `.tplx` 미지원).

        Parameters
        ----------
        path : str | Path
        dsr : bool | None, optional
        """
        eco2 = core.Eco2(
            header=self.eco2.header,
            ds=self.xml.tostring('DS'),
            dsr=self.xml.tostring('DSR'),
        )
        eco2.write(path, dsr=dsr)

    def set_walls(
        self,
        uvalue: float,
        surface_type: SurfaceType = '외벽(벽체)',
        *,
        if_empty: Level = 'debug',
    ) -> Self:
        """
        벽체 설정.

        Parameters
        ----------
        uvalue : float
        surface_type : SurfaceType, optional
        if_empty : Level, optional
            대상 `surface_type`에 해당하는 element가 없을 때 동작.

        Returns
        -------
        Self

        Raises
        ------
        ElementNotFoundError
        """
        if not (walls := list(self.xml.surfaces_by_type(surface_type))):
            if if_empty == 'raise':
                raise ElementNotFoundError(surface_type)

            logger.log(if_empty.upper(), '`{}`이 존재하지 않음.', surface_type)

        for w in walls:
            if w.findtext('code') == '0':
                continue

            self.xml.set_wall_uvalue(wall=w, uvalue=uvalue)

        return self

    def set_windows(
        self,
        uvalue: float | None = None,
        shgc: float | None = None,
        surface_type: SurfaceType = '외부창',
        *,
        update_zero_shgc: bool = False,
        if_empty: Level = 'debug',
    ) -> Self:
        """
        창 설정.

        Parameters
        ----------
        uvalue : float | None, optional
        shgc : float | None, optional
        surface_type : SurfaceType, optional
        update_zero_shgc : bool, optional
            기존 SHGC가 0일 때 (문으로 추정) 수정 여부.
        if_empty : Level, optional
            대상 `surface_type`에 해당하는 element가 없을 때 동작.

        Returns
        -------
        Self

        Raises
        ------
        EditorError
        ElementNotFoundError
        """
        if uvalue is None and shgc is None:
            msg = f'{uvalue=}, {shgc=}'
            raise EditorError(msg)

        if not (windows := list(self.xml.surfaces_by_type(surface_type))):
            if if_empty == 'raise':
                raise ElementNotFoundError(surface_type)

            logger.log(if_empty.upper(), '`{}`이 존재하지 않음.', surface_type)

        for w in windows:
            if w.findtext('code') == '0' and w.findtext('열관류율') == 0:
                continue

            if uvalue is not None:
                self.xml.set_window_uvalue(window=w, uvalue=uvalue)
            if shgc is not None:
                self.xml.set_window_shgc(
                    window=w, shgc=shgc, update_zero=update_zero_shgc
                )

        return self
