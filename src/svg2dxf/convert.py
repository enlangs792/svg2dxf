from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Optional
import xml.etree.ElementTree as ET

import ezdxf
from svgpathtools import Path as SvgPath
from svgpathtools import svg2paths2

_DXF_INVALID_LAYER_CHARS = re.compile(r'[<>/\\":;?*|=]')
_SVG_DRAWABLE_TAGS = {"path", "line", "polyline", "polygon", "rect", "circle", "ellipse"}


@dataclass(frozen=True)
class SvgViewport:
    min_x: float
    min_y: float
    width: float
    height: float


def _parse_viewbox(svg_attributes: dict) -> Optional[SvgViewport]:
    vb = svg_attributes.get("viewBox") or svg_attributes.get("viewbox")
    if not vb:
        return None
    parts = [p for p in str(vb).replace(",", " ").split() if p]
    if len(parts) != 4:
        return None
    try:
        min_x, min_y, w, h = (float(x) for x in parts)
        if w <= 0 or h <= 0:
            return None
        return SvgViewport(min_x=min_x, min_y=min_y, width=w, height=h)
    except ValueError:
        return None


def _strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _pick_layer_name(attrs: dict) -> Optional[str]:
    if not attrs:
        return None

    for key in (
        "{http://www.inkscape.org/namespaces/inkscape}label",
        "inkscape:label",
        "data-layer",
        "data-name",
        "id",
        "class",
    ):
        v = attrs.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def _sanitize_layer_name(name: Optional[str], fallback: str) -> str:
    if not name:
        return fallback
    cleaned = _DXF_INVALID_LAYER_CHARS.sub("_", name).strip()
    if not cleaned:
        return fallback
    return cleaned[:255]


def _extract_group_layers_by_order(svg_path: Path, default_layer: str) -> list[Optional[str]]:
    """
    Collect layer names by SVG document order for drawable elements.
    Each drawable element inherits the nearest parent <g> layer name.
    """
    try:
        root = ET.parse(svg_path).getroot()
    except Exception:
        return []

    layers: list[Optional[str]] = []

    def walk(elem: ET.Element, group_stack: list[str]) -> None:
        tag = _strip_ns(elem.tag).lower()
        current_stack = group_stack

        if tag == "g":
            g_layer = _pick_layer_name(elem.attrib)
            if g_layer:
                current_stack = [*group_stack, _sanitize_layer_name(g_layer, default_layer)]

        if tag in _SVG_DRAWABLE_TAGS:
            own = _pick_layer_name(elem.attrib)
            layer = _sanitize_layer_name(own, default_layer) if own else (current_stack[-1] if current_stack else None)
            layers.append(layer)

        for child in elem:
            walk(child, current_stack)

    walk(root, [])
    return layers


def _bbox_from_paths(paths: Iterable[SvgPath]) -> Optional[SvgViewport]:
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    any_point = False
    for p in paths:
        try:
            bx0, bx1, by0, by1 = p.bbox()
        except Exception:
            continue
        any_point = True
        min_x = min(min_x, bx0)
        max_x = max(max_x, bx1)
        min_y = min(min_y, by0)
        max_y = max(max_y, by1)
    if not any_point:
        return None
    w = max_x - min_x
    h = max_y - min_y
    if w <= 0 or h <= 0:
        return None
    return SvgViewport(min_x=min_x, min_y=min_y, width=w, height=h)


def _sample_path_points(path: SvgPath, step: float, min_points: int = 8) -> list[complex]:
    length = float(path.length(error=1e-4))
    if not (length > 0):
        pt = path.point(0.0)
        return [pt]
    n = max(min_points, int(length / max(step, 1e-6)) + 1)
    pts = [path.point(i / (n - 1)) for i in range(n)]
    return pts


def _to_dxf_xy(
    pt: complex,
    viewport: SvgViewport,
    *,
    scale: float,
    y_flip: bool,
    origin_to_min: bool,
) -> tuple[float, float]:
    x = (pt.real - viewport.min_x) if origin_to_min else pt.real
    y = (pt.imag - viewport.min_y) if origin_to_min else pt.imag

    if y_flip:
        y0 = (viewport.height - y) if origin_to_min else ((viewport.min_y + viewport.height) - y)
        y = y0

    return (float(x) * scale, float(y) * scale)


def convert_svg_to_dxf(
    svg_path: Path,
    dxf_path: Path,
    *,
    scale: float = 1.0,
    step: float = 2.0,
    y_flip: bool = True,
    origin_to_min: bool = True,
    default_layer: str = "SVG",
) -> None:
    paths, path_attributes, svg_attributes = svg2paths2(str(svg_path))
    group_layers = _extract_group_layers_by_order(svg_path, default_layer=default_layer)

    viewport = _parse_viewbox(svg_attributes) or _bbox_from_paths(paths) or SvgViewport(
        min_x=0.0, min_y=0.0, width=100.0, height=100.0
    )

    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()

    for idx, (p, attrs) in enumerate(zip(paths, path_attributes, strict=False)):
        group_layer = group_layers[idx] if idx < len(group_layers) else None
        own_layer = _pick_layer_name(attrs or {})
        layer = group_layer or _sanitize_layer_name(own_layer, default_layer)

        if not doc.layers.has_entry(layer):
            doc.layers.add(name=layer)

        pts = _sample_path_points(p, step=step)
        xy = [_to_dxf_xy(pt, viewport, scale=scale, y_flip=y_flip, origin_to_min=origin_to_min) for pt in pts]

        if len(xy) == 1:
            x0, y0 = xy[0]
            msp.add_point((x0, y0), dxfattribs={"layer": layer})
            continue

        closed = False
        try:
            closed = bool(p.isclosed())
        except Exception:
            closed = False

        msp.add_lwpolyline(
            xy,
            format="xy",
            close=closed,
            dxfattribs={"layer": layer},
        )

    dxf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(dxf_path))


def convert_svgs_in_dir(
    input_dir: Path,
    output_dir: Path,
    *,
    scale: float = 1.0,
    step: float = 2.0,
    y_flip: bool = True,
    origin_to_min: bool = True,
) -> list[Path]:
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    out: list[Path] = []

    for svg in sorted(input_dir.glob("*.svg")):
        dxf = output_dir / (svg.stem + ".dxf")
        convert_svg_to_dxf(svg, dxf, scale=scale, step=step, y_flip=y_flip, origin_to_min=origin_to_min)
        out.append(dxf)

    return out

