# 配置字段表（config-schema）

一份 JSON 描述全部内容：画幅、主题、盒子与连线、状态机、日志列。**模板永远不需要改。**
坐标一律是画布像素（y 向下）；终端主题下拉丁字形宽 0.6em，CJK 字形占两格。
改完配置后必须跑 `check` 子命令做版面自检（它能抓住几何问题，抓不住品味问题——PNG 还要自己看）。

## 顶层字段

| key | 含义 |
| --- | --- |
| `meta` | `{title, lang}` 页面标题与语言 |
| `canvas` | `{preset, width, height, duration, fps, preroll}`；显式 width/height 优先于 preset；`preroll` 秒会加进光点相位，让计数器在 t=0 时就不是零 |
| `theme` | `{preset, font, fontSize, lineHeight, boxMode, radius, borderWidth, wireWidth, packetSize, glow, titlebarStyle, grid, boxTicks, packetShape, colors:{名字:"#rrggbb"}}`；preset 先铺满全部字段，你的值覆盖之，`colors` 按名字逐个合并。`titlebarStyle:"mac"\|"rule"\|"bar"`（三色点窗 / 图签式细线 / GitHub 顶栏）；`grid:true` 网格图纸底；`boxTicks:true` 盒子四角定位标；`packetShape:"dot"\|"diamond"` 光点形状 |
| `clock` | `{start:"HH:MM:SS", rate}` 日志时钟的起点与倍速（rate=3 表示日志时间 3 倍速前进） |
| `titlebar` | `{text, height?, size?}` 终端风标题栏（三色圆点） |
| `credit` | 底部署名/来源行：`{text, y, size?, c?}`（默认 13px、居中、dim 色）。**复刻/改编他人作品必须在此写明出处** |
| `machines` | 状态机表（见下），一切会动的东西 |
| `elements` | 元素列表，按顺序绘制（后画的在上层） |

### 画幅预设 `canvas.preset`

| preset | 尺寸 | 用途 |
| --- | --- | --- |
| `4:5` | 1200×1500 | X / 微博（原版 clip 的比例） |
| `3:4` | 1080×1440 | 小红书 |
| `1:1` | 1080×1080 | 方图 |
| `9:16` | 1080×1920 | 抖音 / 视频号竖屏 |
| `16:9` | 1920×1080 | 横屏 / B 站 / 桌面壁纸 |

坐标是绝对画布像素，所以一份配置对应一个画幅；换比例要另存一份配置重新排版。

### 主题预设 `theme.preset`

| preset | 风格 |
| --- | --- |
| `github-dark` / `github-light` | **GitHub 默认风格**：官方配色（#0d1117 / #ffffff）、系统无衬线字体、6px 圆角细边框、顶栏式标题栏（`bar`）——嵌在 GitHub 页面里毫无违和 |
| `blueprint` | 蓝图工程风：深蓝图纸底 + 网格、白色细线盒 + 四角定位标、菱形光点、图签式标题栏 |
| `terminal-dark` | 深色终端窗、等宽字体、文本模式分段边框盒子、macOS 三色点标题栏 |
| `light-pastel` | 白底粉彩圆角盒子、SVG 圆角箭头、激活项柔光 |

## 元素（elements）

- `text` `{x, y, w?, align, runs | t | text, size?, lh?, c?, b?, ls?, font?, inside?, noCheck?}`
  `y` 是该行垂直中心。`inside:true` 表示故意画在盒子上（图标文字），版面自检会放行；`noCheck:true` 跳过自检。
- `box` `{x, y, w, h, color(边框色), fill?, radius?, border?(px), dash?, container?, pad:[上,左,右?], align, sides:"solid"?, lines:[...], when?, then?:{fill,color,border,glow}}`
  文本行按 lineHeight 顺序往下排。`container:true` 标记"装其他盒子的盒子"，自检跳过它与内部盒子的重叠。`when/then` 在条件成立时整体改样式（`glow` = 颜色名，柔光）。
- `poly` `{points:[[x,y],...], color, width?, r?(圆角), dash?, arrow?:false, head?, opacity?, when?, then?:{color,width,opacity}, stream?:{...}}`
  SVG 折线 + 箭头；`stream` 直接挂在折线上携带光点。**挂了 `stream` 且 `dash:true` 时，流动效果表现为虚线波浪**——加粗亮段沿基础虚线的格子逐格跳动（每 `stream.period` 扫一遍，受 `stream.when` 门控），不再是彗星光点。
- `wire` `{from:[x,y], to:[x,y], dash?, color?, width?}` 轴对齐直连线（结构线，无箭头）。
- `stream` `{path:[[x,y],...], period, offsets?, color, gap?:[y0,y1], tail?, when?}` 光点流：彗星式——单头点带沿行进方向渐隐的渐变尾迹，沿折线循环。所有流的送达总数就是 `{packets}`（图上出现的次数 = 真实送达的光点数）。**短连线（几十 px）只给 1 个 offset**——两个错相光点在短线上会永远同时可见，读起来就是两个点。
- `beam` `{alarm, i, from:[x,y], to:[x,y], head?}` 触发光束：告警机第 i 项亮起时，虚线**逐段放大、从告警侧扫向目标**（一个 `on` 周期扫一遍），熄灭恢复灰色原样；方向自动（向左时箭头为 ◀）。
- `glyph` `{x, y, ch, c, size}` 单字符装饰（如箭头）。
- `rule` `{x, y, w, c?}` 双细线分隔。
- `log` `{x, y, w, rows, padTop?, padBottom?, padLeft?, title, titleX?, titleW?, cols:[{key:"time|who|m|g", x}]}` 事件流面板：新行亮、旧行灰，行数固定。

### 盒子里的行（lines）

一行是字符串或对象：`{runs | t, c, b, align, indent, size, h, items, when, then, alarm}`

- `runs`：字符串或 run 对象 `{t | v | sw | cursor, c, b, size, when, then}`。
  `t` 文本（可含 `{var}`），`v` 变量名，`sw` 色块，`cursor` 闪烁光标。
  `v` 引用的变量若带颜色（状态机输出的对象值），不写 `c` 就自动继承它的颜色。
- `items`：flex 横排 `[{w?, grow?, ml?, align?, runs | bar}]`。
  `bar` = `{w, h, gauge, max?, low?, high?}`（绑定 gauge 状态机，`max` 把原始值归一化，如显存 GB 填 8）或 `{w, h, segments:[{from,to,c}], mark?}`（0~1 分段）。
- `when` / `then`：条件 `{var, eq|ne|in:[...]}`（数组 = AND），成立时覆盖 `{c, b, bg}`。行级 then 作用于整行（如高亮背景）；run 级只改颜色/加粗。
- `alarm: [机器id, 序号]`：侧栏告警行语法糖（`◇/◆` 前缀 + 亮起高亮），等价于一组 when/then 模板。

## 状态机（machines）

一切会动的东西都是状态机，全部是 `t` 的纯函数；**日志由状态机自己产出**，不手写——这是"处处一个事实"的机制保证。

| type | 字段 | 产出变量 |
| --- | --- | --- |
| `ticker` | `start, rate, format:"comma"?, prefix?, suffix?` | `id`（start + rate·t 的累计计数） |
| `cycle` | `values:[字符串 \| {t, m?, g?, c?, ...}], period, t0?, order?, log?:{who,c}` | `id`，`id.i`，`id.<附加字段>`；值对象的 `c` 会自动着色 |
| `gauge` | `values:[数], period, t0?, seed?, threshold, decimals?, bad?:"low"\|"high", low:{label,dest}, high:{label,dest}, lowColor?, highColor?, log?:{who,c,msgs:[...],tail?}` | `id`，`id.num`，`id.low`，`id.bad`，`id.label`，`id.dest` |
| `worst` | `of:[gaugeId...]`，`okText?/okColor?/badText?/badColor?` | `id`（任一 gauge 处于坏状态则坏；带颜色的文本对象） |
| `worker` | `period, run, off?, busy, done:[...], phase?, spin?, busyColor?, doneColor?, log?:{who,c,msgs:[[文本,标签]]}` | `id`（转圈/打勾文本，自带颜色），`id.state` |
| `alarm` | `period, on, t0?, items:[{name, adv:[第一行,第二行], ...}], color, hl?, callsStart?, tokens?:{start,step,unit}, cps?, onText?, offText?, log?:{who,c,start:{m,g},end:{m,g}}` | `id.active`（亮着的序号或 -1），`id.label<i>`，`id.adv0/adv1`（逐字打出），`id.calls`，`id.tokens`，`id.status`，`id.<item 字段>` |

内置变量：`{packets}` 全部光点流的送达总数；`{clock}` 当前日志时钟。日志模板可引用状态机字段，如 `{name}`、`{value}`、`{label}`、`{dest}`。

## 节奏参考值（30 秒、30fps 起步可用）

| 项目 | 取值 |
| --- | --- |
| 光点 period | 每条线 1.5–3s，1–2 个光点、错开 offsets |
| 转圈步进 | 0.3s |
| 日志新增行 | 全机合计每秒 1–1.5 行 |
| gauge 重掷 | 3–5s，各表错开 |
| alarm 周期 / 亮起 | 4.5s / 3s |
| 打字速度 | 0.35s 延迟后每秒 9–10 字 |
| worker 周期 | 7–10s，其中 busy 占 60–75% |
| preroll | 6s 左右，避免 t=0 计数器从零开始 |

## 回放接口

- `window.seek(t)`：画出第 t 秒的帧。`window.__ready` 配置与字体就绪后为 true；`window.__error` 汇集页面错误；`window.__check()` 返回版面问题列表（check 子命令在用）。
- URL 参数：`?manual` 停在 t=0 不自动播放；`?t=秒` 渲染单帧后定格（浏览器里快速查某一帧用）。
