"""Проект почерка (.gfproj): чистый JSON в UTF-8.

{
  "format": "gfproj", "version": 1,
  "name": "...",
  "settings": {...},                      см. ProjectSettings
  "glyphs": {"1072": {"status": "drawn", "source": "user",
                      "variants": [[{"p": [[x, y], ...], "dot": false, "fixed": false}, ...], ...]}}
}

Координаты штрихов — единицы клетки холста (см. geometry.py), до сглаживания:
сглаживание и шаг точек применяются при показе и экспорте, поэтому их можно
менять без перерисовки. fixed = точки уже обработаны (импорт из .gfont или шрифта,
правка точек) и сглаживаются только как есть.
"""

from __future__ import annotations

import copy
import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from gfont.errors import UserError, describe_os_error

from .charsets import ALL_CODES
from .geometry import BASE_CAP, BASELINE, HEIGHT, WIDTH, CellGeometry

FORMAT = "gfproj"
VERSION = 1
MAX_VARIANTS = 5

EMPTY, DRAWN, SKIPPED = "empty", "drawn", "skipped"


@dataclass
class Stroke:
    pts: List[Tuple[float, float]]
    dot: bool = False
    fixed: bool = False

    def to_json(self) -> dict:
        d = {"p": [[round(x, 2), round(y, 2)] for x, y in self.pts]}
        if self.dot:
            d["dot"] = True
        if self.fixed:
            d["fixed"] = True
        return d

    @classmethod
    def from_json(cls, d: dict) -> "Stroke":
        return cls([(float(x), float(y)) for x, y in d.get("p", [])],
                   bool(d.get("dot", False)), bool(d.get("fixed", False)))

    def copy(self) -> "Stroke":
        return Stroke(list(self.pts), self.dot, self.fixed)


@dataclass
class GlyphEntry:
    variants: List[List[Stroke]] = field(default_factory=lambda: [[]])
    status: str = EMPTY
    source: str = ""            # user | font | similar | gfont

    @property
    def strokes(self) -> List[Stroke]:
        return self.variants[0]

    def has_drawing(self) -> bool:
        return self.status == DRAWN and any(self.variants[0])

    def to_json(self) -> dict:
        return {"status": self.status, "source": self.source,
                "variants": [[s.to_json() for s in v] for v in self.variants]}

    @classmethod
    def from_json(cls, d: dict) -> "GlyphEntry":
        vs = [[Stroke.from_json(s) for s in v] for v in d.get("variants", [[]])] or [[]]
        st = d.get("status", EMPTY)
        if st not in (EMPTY, DRAWN, SKIPPED):
            st = EMPTY
        return cls(vs[:MAX_VARIANTS], st, str(d.get("source", "")))

    def copy(self) -> "GlyphEntry":
        return copy.deepcopy(self)


@dataclass
class ProjectSettings:
    smoothing: float = 0.4          # 0..1 (ползунок «Сглаживание» 0–100 %)
    density: float = 1.0            # плотность точек: шаг = 25 / density ед. .gfont
    autoalign: bool = False         # подтягивать низ основы буквы к базовой линии
    size: float = 1.0               # «размер шаблона» 0.8 … 1.2 (масштаб разметки холста)
    normalize: bool = False         # при экспорте: строчные к одной x-height, заглавные к одной высоте
    show_template: bool = True
    template_opacity: float = 0.35
    show_guides: bool = True
    show_order: bool = False        # осевая линия образца с порядком и направлением штрихов
    sample_font: str = ""           # шрифт-образец TTF/OTF; "" = встроенный DejaVu Sans
    hint_gfont: str = ""            # свой шаблон-подсказка .gfont (вместо шрифта)
    template: str = ""              # шаблон .gfont для экспорта; "" = встроенный
    remove_old: bool = True         # убрать из шаблона буквы старого стиля, которых нет в проекте
    alt_mode: str = "none"          # none | plus32768 (см. export.py)
    seed: int = 1
    pen: float = 9.0                # толщина пера в предпросмотре, ед. .gfont
    preview_text: str = "Съешь же ещё этих мягких французских булок, да выпей чаю."

    @classmethod
    def from_dict(cls, d: dict) -> "ProjectSettings":
        p = cls()
        for f in fields(cls):
            if f.name in (d or {}):
                try:
                    setattr(p, f.name, type(getattr(p, f.name))(d[f.name]))
                except (TypeError, ValueError):
                    pass
        p.size = min(1.2, max(0.8, p.size))
        p.smoothing = min(1.0, max(0.0, p.smoothing))
        p.density = min(3.0, max(0.3, p.density))
        return p


class Project:
    def __init__(self, name: str = "Мой почерк"):
        self.name = name
        self.settings = ProjectSettings()
        self.glyphs: Dict[int, GlyphEntry] = {}
        self.path: Optional[Path] = None      # куда сохранён (не пишется в файл)
        self.dirty = False

    # ---- доступ ----
    def geometry(self) -> CellGeometry:
        return CellGeometry(size=self.settings.size)

    def entry(self, code: int) -> GlyphEntry:
        e = self.glyphs.get(code)
        if e is None:
            e = self.glyphs[code] = GlyphEntry()
        return e

    def status(self, code: int) -> str:
        e = self.glyphs.get(code)
        return e.status if e else EMPTY

    def codes(self) -> List[int]:
        extra = sorted(c for c in self.glyphs if c not in set(ALL_CODES))
        return ALL_CODES + extra

    def counts(self) -> Tuple[int, int, int]:
        """(нарисовано пользователем, заполнено автоматически, всего в списке)."""
        user = auto = 0
        for c in ALL_CODES:
            e = self.glyphs.get(c)
            if e and e.has_drawing():
                if e.source in ("", "user", "gfont"):
                    user += 1
                else:
                    auto += 1
        return user, auto, len(ALL_CODES)

    # ---- размер разметки ----
    def set_size(self, size: float) -> None:
        """Сменить «размер шаблона»: штрихи масштабируются вместе с разметкой,
        поэтому их положение относительно линий и итоговый размер не меняются."""
        size = min(1.2, max(0.8, float(size)))
        old = self.settings.size
        if abs(size - old) < 1e-9:
            return
        g = self.geometry()
        f = size / old
        for e in self.glyphs.values():
            for v in e.variants:
                for s in v:
                    s.pts = [(g.cx + (x - g.cx) * f, g.baseline + (y - g.baseline) * f) for x, y in s.pts]
        self.settings.size = size
        self.dirty = True

    # ---- файл ----
    def to_dict(self) -> dict:
        return {"format": FORMAT, "version": VERSION, "name": self.name,
                "cell": {"width": WIDTH, "height": HEIGHT, "baseline": BASELINE, "cap": BASE_CAP},
                "settings": asdict(self.settings),
                "glyphs": {str(c): e.to_json() for c, e in sorted(self.glyphs.items())
                           if e.status != EMPTY or any(e.variants[0])}}

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        if not isinstance(d, dict) or d.get("format") != FORMAT:
            raise UserError("Это не файл проекта почерка (.gfproj).")
        if int(d.get("version", 0)) > VERSION:
            raise UserError("Проект создан более новой версией программы.")
        p = cls(str(d.get("name", "Мой почерк")))
        p.settings = ProjectSettings.from_dict(d.get("settings", {}))
        for k, v in d.get("glyphs", {}).items():
            try:
                code = int(k)
            except ValueError:
                continue
            if 0 < code <= 0xFFFF:
                p.glyphs[code] = GlyphEntry.from_json(v)
        cell = d.get("cell") or {}
        try:
            w0 = float(cell.get("width", WIDTH))
            b0 = float(cell.get("baseline", BASELINE))
            c0 = float(cell.get("cap", BASE_CAP))
        except (TypeError, ValueError):
            w0, b0, c0 = WIDTH, BASELINE, BASE_CAP
        if (w0, b0, c0) != (WIDTH, BASELINE, BASE_CAP) and c0 > 0:
            # клетка другой версии программы: переносим штрихи относительно базовой линии
            f = BASE_CAP / c0
            for e in p.glyphs.values():
                for v in e.variants:
                    for st in v:
                        st.pts = [(WIDTH / 2 + (x - w0 / 2) * f, BASELINE + (y - b0) * f) for x, y in st.pts]
        return p

    def save(self, path) -> None:
        target = Path(path)
        data = json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))
        tmp = target.with_name(target.name + ".tmp")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(data, encoding="utf-8")
            os.replace(tmp, target)
        except OSError as exc:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise UserError(describe_os_error(exc, target)) from exc

    @classmethod
    def load(cls, path) -> "Project":
        p = Path(path)
        try:
            raw = p.read_text(encoding="utf-8")
        except OSError as exc:
            raise UserError(describe_os_error(exc, p, "прочитать")) from exc
        try:
            d = json.loads(raw)
        except ValueError as exc:
            raise UserError(f"Файл «{p.name}» повреждён: {exc}") from exc
        proj = cls.from_dict(d)
        proj.path = p
        return proj
