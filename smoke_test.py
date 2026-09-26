#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""页面冒烟测试：起本地服务 -> 无头浏览器加载 -> 检查渲染结果与控制台错误。"""
import http.server, functools, threading, sys, os, json, time, tempfile
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(ROOT, "docs")
PORT = 8731
TARGET = sys.argv[1] if len(sys.argv) > 1 else "index.html"


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=DOCS)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    httpd.log_message = lambda *a, **k: None
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main():
    serve()
    time.sleep(0.6)
    errors, logs = [], []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1400, "height": 1000})
        pg.on("console", lambda m: (errors if m.type == "error" else logs).append(m.text))
        pg.on("pageerror", lambda e: errors.append("PAGEERROR: " + str(e)))
        pg.goto(f"http://127.0.0.1:{PORT}/{TARGET}", wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(2500)

        result = pg.evaluate("""() => {
          const out = {};
          out.errBox   = !!document.querySelector('.err');
          out.sub      = (document.getElementById('sub')||{}).textContent || '';
          out.cards    = document.querySelectorAll('#cards .card').length;
          out.cardText = (document.querySelector('#cards .card')||{}).innerText || '';
          out.prov     = (document.getElementById('provSel')||{}).value || '';
          out.provN    = (document.getElementById('provSel')||{}).options?.length || 0;
          out.rows     = document.querySelectorAll('#tbl tbody tr').length;
          out.firstRow = (document.querySelector('#tbl tbody tr')||{}).innerText || '';
          out.desc1    = (document.getElementById('desc1')||{}).innerText || '';
          out.desc3    = (document.getElementById('desc3')||{}).innerText || '';
          // 每个图表容器里是否有真实 canvas 且尺寸正常
          out.charts = ['chart1','chart2','chart3'].map(id => {
            const el = document.getElementById(id);
            const c = el ? el.querySelector('canvas') : null;
            return { id, has: !!c, w: c ? c.clientWidth : 0, h: c ? c.clientHeight : 0 };
          });
          // 画布是否真的画了东西（取像素判断非空）
          out.painted = ['chart1','chart2','chart3'].map(id => {
            const c = document.querySelector('#'+id+' canvas');
            if (!c) return { id, nonWhite: 0 };
            const ctx = c.getContext('2d');
            const d = ctx.getImageData(0,0,c.width,c.height).data;
            let n = 0;
            for (let i=0;i<d.length;i+=4*97){ if (d[i+3] > 0 && (d[i]<250||d[i+1]<250||d[i+2]<250)) n++; }
            return { id, nonWhite: n };
          });
          return out;
        }""")

        # 交互测试：切换省份 + 切换油品 + 切换主题
        pg.select_option("#provSel", "北京")
        pg.wait_for_timeout(900)
        after_prov = pg.evaluate("() => document.querySelector('#cards .card:nth-child(2)').innerText")
        chips = pg.query_selector_all("#typeChips .chip")
        if chips:
            chips[3].click()  # 切换 0# 柴油
            pg.wait_for_timeout(800)
        after_chip = pg.evaluate("() => document.getElementById('desc1').innerText")
        pg.click("#themeBtn")
        pg.wait_for_timeout(1200)
        after_theme = pg.evaluate("""() => ({
            theme: document.documentElement.getAttribute('data-theme'),
            painted: (() => { const c=document.querySelector('#chart1 canvas');
              if(!c) return 0; const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
              let n=0; for(let i=0;i<d.length;i+=4*97){ if(d[i+3]>0 && (d[i]<250||d[i+1]<250||d[i+2]<250)) n++; } return n; })()
        })""")
        pg.screenshot(path=os.path.join(tempfile.gettempdir(), "_smoke_light.png"), full_page=False)
        pg.click("#themeBtn")
        pg.wait_for_timeout(1200)
        pg.screenshot(path=os.path.join(tempfile.gettempdir(), "_smoke_dark.png"), full_page=False)
        b.close()

    print("=" * 70)
    print(f"目标页面: {TARGET}")
    print("=" * 70)
    print(f"错误框出现      : {result['errBox']}")
    print(f"副标题          : {result['sub'][:80]}")
    print(f"卡片数量        : {result['cards']}")
    print(f"首卡片内容      : {result['cardText'][:110].replace(chr(10),' | ')}")
    print(f"省份下拉        : {result['prov']} / 共 {result['provN']} 项")
    print(f"表格行数        : {result['rows']}   首行: {result['firstRow'][:60]}")
    print(f"图1描述         : {result['desc1'][:90]}")
    print(f"图3描述         : {result['desc3'][:90]}")
    print(f"图表 canvas     : {result['charts']}")
    print(f"画布非空像素采样: {result['painted']}")
    print("-" * 70)
    print(f"切到北京后卡片  : {after_prov[:90].replace(chr(10),' | ')}")
    print(f"点油品后描述    : {after_chip[:90]}")
    print(f"切主题后        : {after_theme}")
    print("-" * 70)
    print(f"控制台错误 ({len(errors)}):")
    for e in errors[:15]:
        print("   ! " + e[:200])

    ok = (not result["errBox"] and result["cards"] == 3 and result["rows"] == 31
          and all(c["has"] and c["w"] > 100 and c["h"] > 100 for c in result["charts"])
          and all(p["nonWhite"] > 50 for p in result["painted"])
          and len(errors) == 0 and after_theme["painted"] > 50)
    print("=" * 70)
    print("冒烟测试结果    : " + ("全部通过 ✅" if ok else "存在问题 ❌"))
    print("=" * 70)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
