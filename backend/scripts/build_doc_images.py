"""把浏览器验证截图压缩并归档到 `docs/images/`，供 README / MERGE_REPORT 配图使用。

配合 `scripts/browser_check.mjs` 使用：先用它把各页面截到 `.verify/`，再用本脚本归档。

    cd backend
    python scripts/build_doc_images.py

处理规则：
- 统一等比缩放到最大宽度 1400px（Retina 截图降采样后视觉几乎无损，体积显著下降）
- 优先输出优化后的 PNG；若仍超过 400KB 则退回 JPEG（q=88）
- 源文件缺失时跳过并提示，不报错

依赖 Pillow（仅本脚本需要，不在运行/测试依赖内）：

    pip install pillow
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

# backend/scripts/ -> backend/ -> 仓库根目录
ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / ".verify"
DST = ROOT / "docs" / "images"

MAX_W = 1400
JPEG_THRESHOLD = 400 * 1024

# 源文件 -> 目标文件名（用 ASCII，避免跨平台 / CI 上的路径编码问题）
MAPPING = {
    "shot-home.png": "home.png",
    "shot-result.png": "result-overview.png",
    "shot-知识图谱.png": "knowledge-graph.png",
    "shot-每日行程.png": "daily-itinerary.png",
    "shot-天气信息.png": "weather.png",
    "shot-预算明细.png": "budget.png",
    "shot-景点地图.png": "attraction-map.png",
}


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    total = 0

    for src_name, dst_name in MAPPING.items():
        src = SRC / src_name
        if not src.exists():
            print(f"[跳过] 源文件不存在: {src_name}")
            continue

        im = Image.open(src)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")

        if im.width > MAX_W:
            height = round(im.height * MAX_W / im.width)
            im = im.resize((MAX_W, height), Image.LANCZOS)

        out = DST / dst_name
        im.save(out, format="PNG", optimize=True)
        size = out.stat().st_size

        # PNG 仍偏大时，用 JPEG 再压一版（去 alpha、铺白底）
        if size > JPEG_THRESHOLD:
            flat = Image.new("RGB", im.size, (255, 255, 255))
            flat.paste(im, mask=im.split()[-1] if im.mode == "RGBA" else None)
            jpg = out.with_suffix(".jpg")
            flat.save(jpg, format="JPEG", quality=88, optimize=True, progressive=True)
            if jpg.stat().st_size < size:
                out.unlink()
                out, size = jpg, jpg.stat().st_size

        total += size
        print(f"{src_name:>22} -> {out.name:<24} {im.width}x{im.height}  {size / 1024:7.1f} KB")

    print(f"\n合计 {total / 1024 / 1024:.2f} MB，输出目录: {DST}")


if __name__ == "__main__":
    main()
