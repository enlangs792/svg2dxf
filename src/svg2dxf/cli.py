from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .convert import convert_svg_to_dxf, convert_svgs_in_dir


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="svg2dxf",
        description="Convert SVG files to DXF (svgpathtools + ezdxf).",
    )

    p.add_argument(
        "-i",
        "--input",
        default="svgs",
        help="输入目录（包含 .svg），默认：svgs",
    )
    p.add_argument(
        "-o",
        "--output",
        default="out_dxfs",
        help="输出目录（生成 .dxf），默认：out_dxfs",
    )
    p.add_argument(
        "--step",
        type=float,
        default=2.0,
        help="曲线离散化采样步长（越小越精细），默认：2.0",
    )
    p.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="整体缩放比例，默认：1.0",
    )
    p.add_argument(
        "--no-y-flip",
        action="store_true",
        help="禁用 Y 轴翻转（默认会把 SVG 的向下 Y 转成 DXF 的向上 Y）",
    )
    p.add_argument(
        "--keep-origin",
        action="store_true",
        help="不把图形平移到左下角原点（默认会平移到 min x/y 为 0）",
    )
    p.add_argument(
        "--single",
        type=str,
        default=None,
        help="只转换单个 SVG 文件（相对/绝对路径均可）。设置后会忽略 --input 目录批量模式。",
    )
    p.add_argument(
        "--single-out",
        type=str,
        default=None,
        help="单文件模式的输出 dxf 路径（默认同名 .dxf 放到 --output 目录）",
    )

    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    y_flip = not bool(args.no_y_flip)
    origin_to_min = not bool(args.keep_origin)
    step = float(args.step)
    scale = float(args.scale)

    if args.single:
        svg = Path(args.single)
        if not svg.exists():
            print(f"[svg2dxf] SVG 不存在：{svg}", file=sys.stderr)
            return 2
        out_dir = Path(args.output)
        dxf = Path(args.single_out) if args.single_out else (out_dir / (svg.stem + ".dxf"))
        convert_svg_to_dxf(svg, dxf, step=step, scale=scale, y_flip=y_flip, origin_to_min=origin_to_min)
        print(str(dxf))
        return 0

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    if not input_dir.exists():
        print(f"[svg2dxf] 输入目录不存在：{input_dir}", file=sys.stderr)
        return 2

    out = convert_svgs_in_dir(
        input_dir=input_dir,
        output_dir=output_dir,
        step=step,
        scale=scale,
        y_flip=y_flip,
        origin_to_min=origin_to_min,
    )
    print(f"[svg2dxf] 转换完成：{len(out)} 个文件 -> {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

