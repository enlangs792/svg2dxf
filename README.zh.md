# SVG2Dxf

## 介绍

实现 SVG 图片转 DXF。

## 输入目录

- SVG 文件目录：`svgs/`

## 技术方案

- `ezdxf`
- `svgpathtools`

## 管理工具

- `uv`

## 快速开始（uv）

在 `SVG2Dxf/` 目录执行。

安装依赖：

```bash
uv sync
```

批量转换（默认读取 `svgs/`，输出到 `out_dxfs/`）：

```bash
uv run svg2dxf
```

常用参数：

```bash
# 调整采样精度（step 越小越精细）
uv run svg2dxf --step 1.0

# 缩放
uv run svg2dxf --scale 10

# 单文件模式
uv run svg2dxf --single svgs/0001-0001.svg --single-out out_dxfs/0001-0001.dxf
```
