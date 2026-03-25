# SVG2Dxf

## Overview

Convert SVG images to DXF files.

## Input Directory

- SVG source directory: `svgs/`

## Tech Stack

- `ezdxf`
- `svgpathtools`

## Package Manager

- `uv`

## Quick Start (uv)

Run commands in the `SVG2Dxf/` directory.

Install dependencies:

```bash
uv sync
```

Batch conversion (reads from `svgs/` and writes to `out_dxfs/` by default):

```bash
uv run svg2dxf
```

Common options:

```bash
# Sampling precision (smaller step means finer detail)
uv run svg2dxf --step 1.0

# Scale output
uv run svg2dxf --scale 10

# Single-file mode
uv run svg2dxf --single svgs/0001-0001.svg --single-out out_dxfs/0001-0001.dxf
```
