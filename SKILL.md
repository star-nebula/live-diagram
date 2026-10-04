---
name: live-diagram
description: >
  把一份 JSON 配置渲染成"活的架构图"：版面固定的运行动画面板（GitHub 默认风格暗/亮、蓝图工程风、终端暗色风、浅色粉彩信息图风），
  连线上有光点流动、日志滚动、计数跳动、仪表条翻状态、侧栏告警轮转点亮，产出 H.264 mp4
  （适合 X / 小红书 / 抖音 / B 站）或可在浏览器直接打开的动态网页。
  当用户想要：系统架构图 / Agent 分工图 / 数据流图 / 团队运行图"动起来"、"做成监控面板风格的视频"、
  "会动的信息图"、架构图动画、运行态大屏风格演示时使用。
  不适用于：需要交互的图、接真实遥测数据的监控、逐步讲解型动图（那用幻灯片或普通图表工具）。
---

# live-diagram · 活的架构图

把一个系统的描述变成**一直在运行的架构图**：一张固定版面的页面，看起来像正在运行的系统的监控面板。核心机制：

- **一份 JSON 配置**描述全部内容（画幅、主题、盒子、连线、状态机、日志），`assets/template.html` 是通用引擎，**永远不需要改模板**。
- **版面不动，动的是系统状态**。任何一帧截出来都是完整可读的图。
- **确定性渲染**：页面暴露 `window.seek(t)`，一切可见变化都是 `t` 的纯函数（"随机"来自固定种子 hash；无墙钟、无 Math.random、无 CSS 动画）。逐帧 seek + 截图 → ffmpeg 合成；回放逐字节一致，可验证。
- **处处一个事实**：日志行由各状态机在状态变化时自动产出（数值取自它当时的变量），不为屏幕上已有的东西手写日志——数字互相对得上是机制保证的。
- **无真实数据必须标注**：动画自身的计数（packets、calls）在画面上标"示意 / illustrative"；复刻或改编他人作品必须在 `credit` 写明原作者与出处，帖文里同样注明。

## 要求与入口

Python 3.8+（仅标准库）+ Chrome/Chromium/Edge + ffmpeg，全平台可用（Windows 原生支持，无 POSIX 依赖）。

```bash
# 渲染 mp4（同时保留可打开的动态网页）
python scripts/livediagram.py render --config my.json --out my.mp4 --html-out my.html
# 版面自检 + 导出 PNG + 回放一致性验证（退出码非 0 = 有问题）
python scripts/livediagram.py check --config my.json --out-dir frames --repeat
# 只生成动态网页
python scripts/livediagram.py build --config my.json --out page.html
```

网页 URL 参数：`?t=秒` 定格某一帧；`?manual` 停在 t=0。Chrome/ffmpeg 不在 PATH 时用 `--chrome` / `--ffmpeg` 指定。

## 固定流程

1. **收集内容与数字来源。** 列出：有哪些盒子、谁流向谁、哪些是"告警/触发"型侧栏项、日志会说什么。给每个数字注明来源（链接或"示意"）。没有真实来源的数字一律视为示意，并在画面上标明。**先读 `references/motion-grammar.md`**（动法与节奏），再动手。
2. **写配置。** 从最接近的示例复制：`examples/rag-pipeline/config.json`（blueprint 蓝图工程风，4:5，中文，管线 + 告警台 + 仪表 + 工位 + 日志的完整套路）。字段逐条查 `references/config-schema.md`。主题 `theme.preset`：`github-dark`/`github-light`（GitHub 官方配色+系统字体+顶栏，嵌 GitHub 无违和）/ `blueprint`（蓝图工程风）/ `terminal-dark`（终端暗色）/ `light-pastel`（粉彩信息图）。盒子用画布绝对像素排版（预设：`4:5` 1200×1500、`3:4` 1080×1440、`1:1` 1080×1080、`9:16` 1080×1920、`16:9` 1920×1080）；换画幅 = 另存一份配置重排。
3. **渲染。** `render` 子命令（30s@30fps ≈ 900 帧，约几分钟）。`--keep-frames DIR` 可留 PNG 帧。
4. **用帧检查，别用信任。** `check` 子命令在 ~120 个时间点做 DOM 版面测量（文本溢出/重叠/出画布）、导出 PNG、`--repeat` 跳走再跳回比对像素以证明回放一致。**打开 PNG 亲眼看**——检查器抓几何，抓不住品味。修配置 → 重跑，直到退出码 0。

## 动法速记（全文见 references/motion-grammar.md）

- 版面永不移动；没有镜头、没有开场、没有逐步 reveal。
- **三种节奏同时跑**：快（每条线上的光点带尾迹、转圈符、快计数器）+ 中（日志滚动且最新行亮、仪表重掷过阈值翻色翻词、工位转圈⇄打勾）+ 慢（侧栏告警按固定顺序轮流转亮、建议逐字打出、calls/tokens 累计）。
- 节奏参考值：光点 period 1.5–3s 且各线错开；日志全机合计 1–1.5 行/秒；gauge 重掷 3–5s；告警周期 4.5s 亮 3s；打字 9–10 字/秒；`canvas.preroll: 6` 让 t=0 时计数不从零开始。
- 浅色粉彩信息图：保留同一套动法，只换表达——"激活"= 描边加粗 + 柔光（`then:{glow:...}`），用一条主 `cycle` 时间线推导屏幕上一切亮起的东西；复刻他人信息图时不加模块、不改措辞、画面署名。

## 文件

- `assets/template.html` — 通用引擎（配置内嵌 `<!--CONFIG-->` 占位符）。
- `scripts/livediagram.py` — 唯一 CLI：`render` / `check` / `build`。
- `references/motion-grammar.md` — 动法（先读）；`references/config-schema.md` — 配置字段表（写配置时查）。
- `examples/rag-pipeline/` — 完整示例：config.json + 成片 mp4 + 自包含网页 + 截图。

## 状态机一览（详见 config-schema）

| type | 用途 |
| --- | --- |
| `ticker` | 累计计数（速率、token 总量） |
| `cycle` | 轮播状态（路由去向、当前步骤），可携带附加字段与颜色 |
| `gauge` | 仪表重掷 + 阈值翻状态（`bad` 指明哪侧是坏状态） |
| `worst` | 汇总多个 gauge（任一坏则坏） |
| `worker` | 工位转圈 ⇄ 打勾 |
| `alarm` | 侧栏告警轮转（`beam` 元素为其画触发光束） |

条件高亮统一用 `when` / `then`（`{var, eq|ne|in}`，数组 = AND），可用于盒子、折线、光点流、行与 run。
