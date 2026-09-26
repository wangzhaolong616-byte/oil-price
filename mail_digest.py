#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
油价日报 / 调价提醒邮件  /  mail_digest.py
==================================================

按 GitHub Actions 工作流调用。读取 docs/prices.json 中已抓取好的数据，
组装一封可读的纯文本邮件，按 SMTP 协议发出。

设计：
  - 纯 Python 标准库（smtplib + email.mime）
  - 所有凭据均从环境变量读入（由 GitHub Secrets 注入）
  - 失败全部 catch 并写日志（不阻断主数据更新流程）
  - 未配置邮箱凭据时跳过（--user 为空）

使用：
  python mail_digest.py --province 浙江 \\
      --title 油价日报 --to foo@163.com \\
      --from bot@163.com --server smtp.163.com --port 465 \\
      --user bot@163.com --password xxxx
"""
from __future__ import annotations
import argparse
import json
import os
import smtplib
import ssl
import sys
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

CST = timezone(timedelta(hours=8))
ROOT = os.path.dirname(os.path.abspath(__file__))
PRICES = os.path.join(ROOT, "docs", "prices.json")


def fmt(v: float | None, d: int = 2) -> str:
    if v is None:
        return "—"
    s = f"{abs(v):.{d}f}"
    return f"+{s}" if v > 0 else (f"-{s}" if v < 0 else s)


def load() -> dict | None:
    if not os.path.exists(PRICES):
        return None
    try:
        with open(PRICES, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def render(d: dict, province: str) -> tuple[str, str, str]:
    """返回 (邮件主题, 纯文本正文, HTML 正文)。"""
    meta = d["meta"]; nx = d["next"]; rt = d["realtime"]
    pd = d["provinces_data"].get(province) or d["provinces_data"][meta["default_province"]]
    i = len(d["dates"]) - 1
    cur = {k: pd[k][i] for k in ("92", "95", "89", "0")}
    dlt = {k: pd["d" + k][i] for k in ("92", "95", "89", "0")}
    today = d["dates"][i]
    updated = meta["updated_at"][:19].replace("T", " ")

    direction = nx.get("direction", "未知")
    est = nx.get("est_delta_92")
    pct = nx.get("crude_pct")
    days_left = nx.get("days_left", "—")

    # 头部 + 当前油价
    text = []
    text.append(f"✦ 油价日报 · {province}（{today}生效）")
    text.append(f"数据更新：{updated}　|　覆盖 {meta['province_count']} 省 {meta['date_from']} ~ {meta['date_to']} 共 {meta['adjust_count']} 次调价")
    text.append("")
    text.append("本次调价：")
    text.append(f"  · 92# 汽油  {cur['92']:.2f} 元/升  （{fmt(dlt['92'])}）")
    text.append(f"  · 95# 汽油  {cur['95']:.2f} 元/升  （{fmt(dlt['95'])}）")
    text.append(f"  · 89# 汽油  {cur['89']:.2f} 元/升  （{fmt(dlt['89'])}）")
    text.append(f"  · 0# 柴油   {cur['0']:.2f} 元/升  （{fmt(dlt['0'])}）")
    text.append("")
    text.append("下次调价窗口预测：")
    text.append(f"  · 日期       {nx.get('date', '—')}（还有 {days_left} 天）")
    text.append(f"  · 方向       {direction}")
    if pct is not None:
        text.append(f"  · 原油变化   {pct:+.2f}%（本轮均价 {nx.get('window_now_avg')}，上一轮 {nx.get('window_last_avg')}）")
    if est is not None:
        text.append(f"  · 估算幅度   {est:+.3f} 元/升（依据 {nx.get('samples', 0)} 次历史样本拟合 k={nx.get('k')}）")
    text.append(f"  · 备注       {nx.get('reason', '')}")
    text.append("")
    text.append("国际原油（实时）：")
    text.append(f"  · 布伦特  {rt.get('brent', '—'):.2f}  美元/桶")
    text.append(f"  · WTI    {rt.get('wti', '—'):.2f}  美元/桶")
    text.append(f"  · 报价时间 {rt.get('ts', '—')}")
    text.append("")
    text.append("—")
    text.append("本邮件由 GitHub Actions 自动生成。最终加油价格以加油站挂牌价为准。")
    text.append("详细图表见：你的 GitHub Pages 链接。")

    html = f"""<!doctype html>
<html><body style="font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;color:#1f2937;max-width:560px">
<h2 style="color:#4a9eff;margin:0 0 6px">✦ 油价日报 · {province}</h2>
<div style="color:#6b7280;font-size:12px;margin-bottom:14px">生效 {today} · 数据更新 {updated}</div>

<div style="background:#f5f7fa;border-left:3px solid #4a9eff;padding:10px 14px;border-radius:6px;margin-bottom:14px">
  <b>下次调价窗口：</b>{nx.get('date', '—')}（还有 {days_left} 天）<br>
  <b>方向：</b><span style="color:{('#e5484d' if '上调' in direction else ('#30a46c' if '下调' in direction else '#64748b'))};font-weight:600">{direction}</span>
  {f'<br><b>估算：</b><span style="font-weight:600">{est:+.3f} 元/升</span>（原油变化 {pct:+.2f}%）' if est and pct is not None else ''}
</div>

<table style="width:100%;border-collapse:collapse;font-size:14px">
<thead><tr style="background:#eef2f6">
  <th style="text-align:left;padding:8px">品类</th>
  <th style="text-align:right;padding:8px">当前价</th>
  <th style="text-align:right;padding:8px">涨跌</th></tr></thead>
<tbody>
<tr><td>92# 汽油</td><td style="text-align:right">{cur['92']:.2f}</td><td style="text-align:right;color:{'#e5484d' if dlt['92']>0 else('#30a46c' if dlt['92']<0 else '#64748b')}">{fmt(dlt['92'])}</td></tr>
<tr><td>95# 汽油</td><td style="text-align:right">{cur['95']:.2f}</td><td style="text-align:right;color:{'#e5484d' if dlt['95']>0 else('#30a46c' if dlt['95']<0 else '#64748b')}">{fmt(dlt['95'])}</td></tr>
<tr><td>89# 汽油</td><td style="text-align:right">{cur['89']:.2f}</td><td style="text-align:right;color:{'#e5484d' if dlt['89']>0 else('#30a46c' if dlt['89']<0 else '#64748b')}">{fmt(dlt['89'])}</td></tr>
<tr><td>0# 柴油</td><td style="text-align:right">{cur['0']:.2f}</td><td style="text-align:right;color:{'#e5484d' if dlt['0']>0 else('#30a46c' if dlt['0']<0 else '#64748b')}">{fmt(dlt['0'])}</td></tr>
</tbody>
</table>

<div style="margin-top:14px;color:#64748b;font-size:12px;line-height:1.7">
国际原油实时：布伦特 {rt.get('brent', '—')} 美元/桶　·　WTI {rt.get('wti', '—')} 美元/桶（{rt.get('ts', '—')}）<br>
{nx.get('reason', '')}
</div>

<hr style="border:none;border-top:1px solid #eef2f6;margin:18px 0">
<div style="color:#9ca3af;font-size:11px">本邮件由 GitHub Actions 自动生成。最终加油价格以加油站挂牌价为准。</div>
</body></html>"""

    subj = (f"[油价日报] {province} {direction}"
            + (f" 估算 {est:+.2f} 元/升" if est is not None else "")
            + f" · {today}")
    return subj, "\n".join(text), html


def send(args) -> bool:
    if not (args.user and args.password and args.to and args.server):
        print("[mail] 邮箱凭据未配置，跳过发送", file=sys.stderr)
        return False
    d = load()
    if not d:
        print("[mail] 无法读取 prices.json，跳过", file=sys.stderr)
        return False

    subj, text, html = render(d, args.province)
    from_addr = args.from_addr or args.user
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subj
    msg["From"] = from_addr
    msg["To"] = args.to
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        port = int(args.port or 465)
        ctx = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(args.server, port, timeout=30, context=ctx) as s:
                s.login(args.user, args.password)
                s.sendmail(from_addr, [args.to], msg.as_string())
        else:
            with smtplib.SMTP(args.server, port, timeout=30) as s:
                s.starttls(context=ctx)
                s.login(args.user, args.password)
                s.sendmail(from_addr, [args.to], msg.as_string())
        print(f"[mail] 已发送到 {args.to}，主题：{subj}")
        return True
    except Exception as exc:
        print(f"[mail] 发送失败：{exc}", file=sys.stderr)
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--province", required=True)
    ap.add_argument("--title", default="油价日报")
    ap.add_argument("--to", default=os.environ.get("MAIL_TO", ""))
    ap.add_argument("--from", dest="from_addr", default=os.environ.get("MAIL_FROM", ""))
    ap.add_argument("--server", default=os.environ.get("MAIL_SERVER", ""))
    ap.add_argument("--port", default=os.environ.get("MAIL_PORT", "465"))
    ap.add_argument("--user", default=os.environ.get("MAIL_USERNAME", ""))
    ap.add_argument("--password", default=os.environ.get("MAIL_PASSWORD", ""))
    args = ap.parse_args()
    ok = send(args)
    return 0 if ok else 0   # 邮件失败不报错（不阻断主流程）


if __name__ == "__main__":
    sys.exit(main())