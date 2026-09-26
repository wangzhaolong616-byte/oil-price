#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 docs/index.html + docs/vendor/echarts.min.js + data/prices.json
合成成 docs/oil-price-offline.html（自包含单文件，可离线打开/分享/保存）。

产出 ~1.5 MB：
  - 内嵌 ECharts（1 MB）
  - 内嵌价格数据（~0.5 MB，压缩后）
  - 纯静态、无任何外部依赖
"""
from __future__ import annotations
import json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(ROOT, "docs", "index.html")
ECHARTS = os.path.join(ROOT, "docs", "vendor", "echarts.min.js")
PRICES = os.path.join(ROOT, "docs", "prices.json")
OUT = os.path.join(ROOT, "docs", "oil-price-offline.html")

# 占位符用 ECharts 内嵌区块 + 数据内嵌区块
ECHARTS_PLACEHOLDER = "<!-- __EC_INLINE__ -->"
DATA_PLACEHOLDER = "<!-- __DATA_INLINE__ -->"


def main() -> int:
    if not os.path.exists(HTML):
        print(f"找不到 {HTML}", file=sys.stderr); return 1
    if not os.path.exists(ECHARTS):
        print(f"找不到 {ECHARTS}", file=sys.stderr); return 1
    if not os.path.exists(PRICES):
        print(f"找不到 {PRICES}", file=sys.stderr); return 1

    html = open(HTML, encoding="utf-8").read()
    echarts = open(ECHARTS, encoding="utf-8", errors="replace").read()
    data = json.loads(open(PRICES, encoding="utf-8").read())

    # 检查两个占位符是否存在
    for ph in (ECHARTS_PLACEHOLDER, DATA_PLACEHOLDER):
        if ph not in html:
            print(f"HTML 中缺少占位符 {ph}", file=sys.stderr)
            print("请在 docs/index.html 的 </head> 之前加上一行：",
                  file=sys.stderr)
            print(f"  {ECHARTS_PLACEHOLDER}", file=sys.stderr)
            print(f"  {DATA_PLACEHOLDER}", file=sys.stderr)
            return 1

    # 构造内嵌块
    echarts_block = f'<script>/* ECharts v5.5.1 内嵌 {len(echarts)} bytes */\n{echarts}\n</script>'
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    data_block = f'<script>window.__OIL_DATA__={data_json};</script>'

    out_html = html.replace(ECHARTS_PLACEHOLDER, echarts_block, 1)
    out_html = out_html.replace(DATA_PLACEHOLDER, data_block, 1)
    # 去掉原来的外链 script（已被内联块取代），否则 ECharts 会被注册两次
    out_html = re.sub(
        r'<script\s+src="vendor/echarts\.min\.js"[^>]*>\s*</script>',
        '', out_html, count=1)

    # 离线单文件不应引用任何外部资源，去掉 PWA 相关引用（否则会 404）
    for pat in (
        r'<link\s+rel="manifest"[^>]*>\s*',
        r'<link\s+rel="icon"[^>]*>\s*',
        r'<link\s+rel="apple-touch-icon"[^>]*>\s*',
    ):
        out_html = re.sub(pat, '', out_html)

    # 顶部加身份说明，方便一眼认出这是离线版
    banner = (
        "<!--\n"
        "  ============================================================\n"
        "  中国油价趋势看板 · 离线版（docs/oil-price-offline.html）\n"
        "  ------------------------------------------------------------\n"
        "  本文件由 build_standalone.py 自动生成，请勿手工编辑。\n"
        "  ECharts 与价格数据已全部内嵌 —— 双击即可打开，无需联网、无需服务器。\n"
        f"  内嵌数据时间点：{data['meta']['updated_at'][:19].replace('T', ' ')}\n"
        f"  覆盖 {data['meta']['province_count']} 省，"
        f"{data['meta']['date_from']} ~ {data['meta']['date_to']}，"
        f"共 {data['meta']['adjust_count']} 次调价\n"
        "  ============================================================\n"
        "-->\n"
    )
    out_html = banner + out_html

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(out_html)

    size = os.path.getsize(OUT)
    print(f"✓ 写出 {OUT}")
    print(f"  内嵌数据  : {len(data_json):>10,} 字节")
    print(f"  内嵌 ECharts : {len(echarts):>10,} 字节")
    print(f"  总体积    : {size:>10,} 字节  ({size/1024/1024:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())