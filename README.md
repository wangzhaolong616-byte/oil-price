# 中国大陆油价趋势看板

> 自动抓取、可视化、可邮件提醒的**完全免费**方案。部署一次，GitHub Actions 每天自动跑，无需任何持续维护。

---

## 📦 文件速查表（先搞清楚每个文件是干嘛的）

| 文件 | 类型 | 你要关心的程度 | 说明 |
|---|:--:|:--:|---|
| **`docs/index.html`** | 🌐 **在线版页面** | 👀 **看这个** | GitHub Pages 托管的主页面。浏览器打开就是你看到的看板。数据靠同目录 `docs/prices.json` 供给 |
| **`docs/oil-price-offline.html`** | 💾 **离线版页面** | 👀 **看这个** | **1.5 MB 单文件**，ECharts + 数据全内嵌。双击就能开，**不用联网、不用服务器**，可存手机/发微信 |
| `docs/prices.json` | 📊 数据（给在线版用） | 自动 | 495 KB 价格数据，由 `fetch_oil.py` 每次抓取后自动覆盖 |
| `docs/vendor/echarts.min.js` | 📚 图表库 | 不用管 | ECharts 5.5.1（1 MB）。**刻意放在本地**，避免依赖 CDN 挂掉 |
| `docs/.nojekyll` | ⚙️ 配置 | 不用管 | 告诉 GitHub Pages 别用 Jekyll 处理，否则 `vendor/` 会被吞掉 |
| **`fetch_oil.py`** | 🔧 **源码 · 核心** | 想改就看这 | 抓取脚本。抓东财 + 新浪 + FRED + 腾讯，做多源对账，算出下次调价预测。**纯标准库，零依赖** |
| **`build_standalone.py`** | 🔧 源码 | 不用管 | 把 `index.html` + ECharts + 数据 → 合成离线单文件版 |
| **`mail_digest.py`** | 🔧 源码 | 配邮件才用 | 生成并发邮件日报（纯 `smtplib`，无第三方库） |
| `smoke_test.py` | 🧪 测试 | 不用管 | 无头浏览器冒烟测试：检查 3 张卡片、31 行表格、3 个图表是否渲染正常 |
| **`.github/workflows/update.yml`** | ⚙️ **源码 · 自动化** | 想改频率看这 | GitHub Actions 工作流。每天 3 次自动跑：抓取 → 生成离线版 → 提交 → 发邮件 |
| `data/prices.json` | 📊 数据存档 | 不用管 | 与 `docs/prices.json` 同内容，留作存档/备份 |
| `README.md` | 📖 说明 | 👀 | 本文件 |
| `LICENSE` | ⚖️ 协议 | 不用管 | MIT |

> **一句话**：看板本体就是 `docs/index.html`（在线）和 `docs/oil-price-offline.html`（离线）这两个 HTML；其它全是让它们每天自动更新的"后台机器"。

一个数据驱动、零依赖的开源看板：

- **覆盖范围**：全国 31 个省级行政区、2008-06-21 至今、303 次调价、92#/95#/89# 汽油与 0# 柴油
- **国际对照**：布伦特、WTI 日度历史（1986 起）
- **预测下次调价**：基于历史规律拟合的窗口、方向、估算幅度（仅供参考，以发改委公告为准）
- **完全免费**：部署在 GitHub Pages（公开仓库 Actions 无时长限制），无服务器、无信用卡、无实名
- **邮件提醒**：可配置 SMTP，调价日报自动推送

![深色主题示意](https://via.placeholder.com/1200x600/161d26/8b98a9?text=dark+theme+screenshot)
> 在本地 `python smoke_test.py` 可重新生成截图并打印渲染校验结果。

---

## 1. 数据来源（全部免费、实测可用）

| 用途 | 来源 | 覆盖 | Key |
|---|---|---|---|
| **国内成品油零售价**（核心） | [东方财富数据中心](https://data.eastmoney.com/cjsj/oil_city.html) `RPTA_WEB_YJ_JH` | 31 省 × 92/95/89/0# × 303 个调价日 | 无需 |
| **国际原油日度历史**（主源） | 新浪财经外盘日 K | WTI: 1996 起 / 布伦特: 2016 起 | 无需 |
| **国际原油日度历史**（早期补齐） | [FRED St. Louis Fed](https://fred.stlouisfed.org/series/DCOILBRENTEU) DCOILBRENTEU/DCOILWTICO | 1986 起，**仅在拼接前做量级校验** | 无需 |
| **国际原油实时报价** | 新浪 `hq.sinajs.cn` / 腾讯 `qt.gtimg.cn` 双通道 | 当日 | 无需 |

### 多源对账机制（保证数据可靠）

> **实测发现**：FRED 与新浪在历史上吻合（中位偏差 0.3%~1.5%），但 FRED **最近若干天偶发异常偏移**（2026-09 实测布伦特偏差达 20 美元）。腾讯独立源交叉验证新浪是准的。
>
> 因此 `fetch_oil.py` 内建多源对账：
> - 以新浪为主源
> - FRED 仅用于"新浪覆盖不到"的早期区间，拼接前自动等比缩放（消除接缝台阶）
> - 实时报价双通道兜底（新浪 → 腾讯）
> - 任一源异常都不会污染历史曲线

---

## 2. GitHub 调研结论

我把 GitHub 上相关的开源仓库都过了一遍，**没有一个能同时满足"自动抓取 + 趋势图 + 完全免费 + 零维护"四项**。最接近的两个各自只解决了半边问题，所以本项目站在它们的肩膀上自建。

| 项目 | 借鉴之处 | 缺什么 |
|---|---|---|
| [elephi/ChinaGasPriceWatch](https://github.com/elephi/ChinaGasPriceWatch) | 验证了东方财富 datacenter API 可行性；做了 Brent/WTI 窗口对齐 | 本地脚本、无定时、需手动跑 |
| [duhailong1/oil-price](https://github.com/duhailong1/oil-price) | 零依赖单文件 HTML 思路 | 仅当日快照、无历史 |
| [maoxiaomo/China-Oil-Price-New](https://github.com/maoxiaomo/China-Oil-Price-New) | 印证东财 API 比网页爬虫更稳；节假日 API 算下次调价日 | Home Assistant 集成、非独立可视化 |

---

## 3. 架构

```
                   ┌─────────────────────────────────────┐
                   │  GitHub Actions（每天 3 次 cron）       │
                   │                                       │
                   │  1. fetch_oil.py 增量抓取 → prices.json│
                   │  2. build_standalone.py 生成离线版     │
                   │  3. git commit + push                 │
                   │  4. (可选) mail_digest.py 发邮件日报    │
                   └─────────────────┬─────────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              ▼                      ▼                      ▼
      data/prices.json        docs/index.html      docs/oil-price-offline.html
       （数据层）             （GitHub Pages 托管）     （单文件离线版，1.5 MB）
```

**为什么是 GitHub Actions + Pages：**
- 公开仓库 Actions **无时长限制**、Pages **完全免费**
- 无需服务器、无需信用卡、无需实名
- 每日多次 commit 自维持，**不会触发 60 天停用策略**
- 同一份数据可同时给 Pages 在线版和单文件离线版使用

---

## 4. 部署指南（5 分钟）

### 4.1 克隆/创建仓库

```bash
# 在 GitHub 上创建一个新的 PUBLIC 仓库，名字随意（如 oil-price）
git clone https://github.com/<你的用户名>/oil-price.git
cd oil-price
# 把本目录的全部内容拷过去
git add . && git commit -m "init"
git push
```

### 4.2 开启 GitHub Pages

进入仓库 → **Settings** → **Pages** → **Source** 选 **Deploy from a branch** → Branch 选 `main` → Folder 选 **`/docs`** → Save。

### 4.3 触发首次抓取

进入 **Actions** 标签 → 选 `update-oil-price` 工作流 → **Run workflow** → 勾选 **full** 强制全量 → Run。

第一次需要 2 分钟左右（15 页东财 + FRED + 新浪）。完成后：
- `data/prices.json` 有 495 KB 数据
- `docs/prices.json` 同上
- `docs/oil-price-offline.html` 是 1.5 MB 单文件

然后访问 `https://<你的用户名>.github.io/<仓库名>/`（首次 Pages 部署需要再等 1~2 分钟生效）。

### 4.4 配置邮件提醒（可选）

如果想接收每日邮件，进入 **Settings** → **Secrets and variables** → **Actions** → **New repository secret** 添加：

| Secret 名 | 内容 | 例 |
|---|---|---|
| `MAIL_SERVER` | SMTP 服务器域名 | `smtp.163.com` / `smtp.qq.com` / `smtp.gmail.com` |
| `MAIL_PORT` | 端口（SSL=465，STARTTLS=587） | `465` |
| `MAIL_USERNAME` | 登录用户名（一般是邮箱地址） | `mybot@163.com` |
| `MAIL_PASSWORD` | **授权码**（不是登录密码，QQ/163/Gmail 都需要在邮箱后台单独生成） | `ABCDXYZXYZABC` |
| `MAIL_FROM` | 显示的发件人邮箱 | `mybot@163.com` |
| `MAIL_TO` | 收件人 | `your@email.com` |

保存后再跑一次工作流即可生效。

> **国内推荐**：163 邮箱（`smtp.163.com`）或 QQ 邮箱（`smtp.qq.com`）。先到邮箱"设置→客户端授权密码"生成授权码，再把授权码填到 `MAIL_PASSWORD`。

---

## 5. 本地运行（不想部署 GitHub 也行）

```bash
# 首次全量抓取（300+ 调价日，2009-至今）
python fetch_oil.py --full

# 生成单文件离线版
python build_standalone.py

# 直接打开
open docs/oil-price-offline.html   # 或双击 / 用浏览器拖入
```

也可以：

```bash
# 启动本地预览服务
python -m http.server 8000 -d docs
# 浏览器访问 http://localhost:8000/index.html
```

---

## 6. 目录树

```
china-oil-price/
├── 🌐 docs/index.html              ← 在线版（GitHub Pages 托管）
├── 💾 docs/oil-price-offline.html   ← 离线版（1.5 MB 单文件，双击即开）
├── 📊 docs/prices.json              ← 在线版读的数据（自动更新）
├── 📚 docs/vendor/echarts.min.js    ← ECharts 本地副本
├── ⚙️  docs/.nojekyll                ← 禁用 Jekyll
│
├── 🔧 fetch_oil.py                  ← 核心抓取脚本
├── 🔧 build_standalone.py           ← 生成离线版
├── 🔧 mail_digest.py                ← 邮件日报
├── 🧪 smoke_test.py                 ← 渲染冒烟测试
│
├── ⚙️  .github/workflows/update.yml   ← 每天自动跑的定时任务
├── 📊 data/prices.json              ← 数据存档
├── 📖 README.md
└── ⚖️  LICENSE
```

---

## 7. 调色约定（强约束）

| 涨跌 | 颜色 |
|---|---|
| ↑ 上调 | **红** `#e5484d`（`#d92626` 浅色主题） |
| ↓ 下调 | **绿** `#30a46c`（`#128a52` 浅色主题） |

与 A 股一致。国际通用配色习惯的**反向**。本项目默认按中国大陆习惯。

---

## 8. 已知限制与免责

- **预测仅为估算**：基于历史 8 次调价间隔中位数 + 140 次拟合得到的 k 系数推算，**最终以国家发改委公告为准**
- **节假日**：脚本用"间隔中位数 + 周末顺延"近似，遇春节等长假会偏差 1~2 天
- **国内价格口径**：采用东财省/直辖市/自治区级零售基准价，与个体加油站实际挂牌价可能小幅差异
- **数据来源善意使用**：脚本请求频率低（每次不到 15 次请求），请勿高并发滥用

---

## 9. 维护说明（你大概率不需要看这里）

- 每月看一下 Actions 是否在跑（绿色 ✓ 表示正常）
- 如果看到失败，点击失败详情看日志——通常是东财接口偶发超时，重跑即可
- 60 天无 commit 会被 GitHub 暂停 scheduled workflow → 本项目每次抓取都会 commit，**自维持**
- FRED 偶发换接口字段 → 自动拼接校验会丢弃并打印日志

---

## 10. License

MIT