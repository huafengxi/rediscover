# Rediscover 发布手册

课程目录 `/rediscover/`。`/rediscover/<ID>/` 默认阅读（也可显式写 `?mode=read`）；`/rediscover/<ID>/?mode=quiz` 直达答题。`/rediscover/health` 返回运行版本、课程数和推理能力。服务只绑定 loopback；从 dev Web 入口访问时沿用原有 BasicAuth。不要把应用直连端口暴露到网络。

## 内容与判定

以 [`courses/A03.md`](../courses/A03.md) 为样板。每个 `@@` 后是单行 JSON（至少有 `id`、`title`），再接 Markdown 正文（段落、三级标题、引用、强调、代码及课程/HTTPS 链接）。标题与任务取课程地图。两种模式按同一个步骤顺序渲染正文、图、题面和 `solution`。写脱离交互也读得通的过渡；题面不要依赖「在这个栏里」之类的界面参照。

- `reading_gate: "看两站记录"` 放在证据**所在的步骤**；按钮在此前出现，本步到下一门之前的常规段落随点击一次展开。`compare: "<前一预测步 ID>"` 自动成阅读门（缺省按钮为「看观测结果」），答题可对照原话或略过。不要用门分页普通正文，不要把证据及解答写进门前的题面、图注或替代文字。阅读显示已到达步骤的 `solution`，不写作答记录。
- 答题按原步骤开放；表达式或解释题可用 `question.hints` 提供按顺序主动请求的提示（从关系提示到具体步骤）。`question.hint` 是通用错误反馈，`partial` 可为具体中间值或误算写反馈。`solution` 是 Markdown；默认主动查看才显示，设置 `solution_on_pass: true` 则通过该题后也显示。示例式、预期值和解释判据留在服务端。用 `checks/build.py` 编译、用 `checks/flow.py` 实走。
- `figure: [类型, 数据, 图注, 替代描述]`；原有 `nodes` / `plot` / `bars` / `grid` / `strips` 的三项配置仍可载入（图注兼作 `alt`）。新版手稿显式写第四项替代描述，正文引用图号；简短说出读者在图里应看到的关系。独立教学分图可附 `figure_panels: ["子图一的教学用途", "子图二的教学用途"]`，以便新版门槛登记用途并人工复核。
- 自定义图用 `figure: ["diagram", "文件名不带后缀", "图注", "替代描述"]`，数据放在本课 `courses/<ID>/<文件名>.json`（文件名限小写字母、数字、连字符）。例见 [A03 剖面](../courses/A03/section.json)。JSON 格式为 `{"height": 260, "draw": [["line",20,40,80,40,"guide"],["label",80,30,"参照线","start"]]}`。画布固定宽 400、高 100–480；坐标原点在左上。支持 `line,x1,y1,x2,y2,笔型`、`circle,cx,cy,r,笔型`、`arc,cx,cy,r,起角,止角,笔型`（向右为 0°，顺时针为正，弧跨小于 360°）、`dot,x,y`、`label,x,y,文字,对齐`。笔型选 `ink`、`light`、`guide`（虚线）、`measure`、`surface`、`circle`；文字对齐选 `start/middle/end`。不接受 SVG 源码、脚本、外部文件或资源地址。手机与桌面都要实看图注、数字和线是否辨得清。

`continue`、`submit`、`skip`、`reveal` 和 `hint` 均由 SQLite 事务记录；阅读门保存在另一张表，读位置按课件版本、模式、浏览器标签页保存。阅读用独立的只读视图和带门的图片路径；答题图片仍只在答题本步开放后提供。作答、查看推导、阅读开门各不混记。表达式只支持有限数字算术，以分数精确计算，作者可设置容差、部分结果及所需原始数据。改步骤次序、ID、判题意义或阅读门顺序时提升该课 `version`；旧版本进度仍留在数据库，不套到新证据顺序。答案进入进度 DB；没有发送答案或凭据的遥测。

## 分批写课与审阅

1. 从[课程地图](curriculum-map.md)抄准 ID、标题和完成成果。先离开交互顺读一遍草稿：开头提问 → 尝试及它为何合理 → 哪条证据使它不够 → 修正 → 独立复核。只在读者需要先猜再看的地方设阅读门。用一条新数据、反例或留出的观测检验结果，不用原来拟合模型的数据再证明模型。
2. 为每幅图写一句「看这幅图才能更容易理解什么」，从正文指到图号。检查对象名、方向、单位和比例；用线型或标签补足颜色；分别看手机和桌面。预先可见的图（包括替代描述、图注、标题和按比例画出的形状）不能泄露后面的证据。A03 图 1 用另一个练习点控制时刻，不画出预测所问的 B 站正午实测；图 2 才给两站记录。
3. 计算题写清量到算式的中间关系和单位；自己试两种等价式、部分结果、典型误算和只填数值。提示先指关系，再给下一步。预测/解释题不是填关键词：明确要比较哪些记录或模型；证据后再要求解释。B01 可作兼容的非算式判据示例：评阅是否把两个称量范围和数量关系连接起来，而非只认「天平」；没有模型时仍能读作者解释。为证明、因果、设计课选相称的检查，不强加算式。
4. 每组先用 `checks/build.py --reading-standard --course <ID> …`（每个 ID 重复 `--course`）和 `checks/flow.py … --course <ID> …` 查自己的课，再逐课人工填表。记录一次会改变判断的图或题，不只写「通过」。全量通过与上线另做，单组检查不等于已发布。

| 课号 | 阅读过渡（失败 → 修正） | 两幅图或独立分图各帮什么 | 作答前能看到什么 / 提示或判据 | 算式或独立证据复核 | 两种模式及视口、缺口 |
| --- | --- | --- | --- | --- | --- |
| A03 | 错时比较混入时间 → 同经线同步 | 图 1 控制时间；图 2 读角；图 3 等角；图 4 配对弧与整圈 | 预测前只有练习点对照；列式时图 4 已开，第一条提示问 C 所配的角 | `800/(7.2/360)` 与 `800×360/7.2`；迁移用 660 km / 6°；第三站独立复测 | 记首次阅读及两种视口的截图或具体步骤 |

以下是五组选择「第二图／独立复核」的方向例，不是已审课结论：A–B 用两地观测与测量范围对照，另取位置或观测条件；C–E 用变换前后、截面或模型与轨迹对照，换对象或留出一段读数；F–H 用机构、能量收支或逐状态流程，换载荷、输入或消息；I–K 用竞争模型的不同预测、分组数据或图上的替代路径，换样本或用反例；L–N 用反馈前后、相位/信号或时序图，拿未用于调参的扰动或下一条记录交叉验证。

## dev 发布

1. 构建通过后把 commit 及唯一 `deploy-*` tag 推到项目 `origin`。在 `~/m/run/local/data/rediscover/releases/<tag>/` 装配该 tag（例如新建目录后 `git archive <tag> | tar -x -C <release>`），部署快照不由日常工作树运行。
2. 把状态单独放在 `~/m/run/local/data/rediscover/state/`（含 SQLite、WAL 和会话签名密钥；备份时一并保留）；依赖与模型也在发布目录之外。`requirements-dev-service.txt` 用单独的 `--system-site-packages` venv 装配；PyTorch、Transformers 使用 dev 既有 Python 运行时。可选 `REDISCOVER_SPEECH_MODEL` 指向已下载的 Vosk Small CN 目录，可选 `REDISCOVER_LOCAL_AI_MODEL` 指向已校验的本地 Qwen 模型目录。加载只读、本地、无自动下载、禁用远程模型代码。输出只作为当前步的有限判据标签；给读者的反馈来自作者，读者可随时直接展开作者解释。只有显式授权使用 OpenAI 兼容适配器的部署才配置 `REDISCOVER_AI_URL`、`REDISCOVER_AI_MODEL` 及从既有授权配置注入的 `REDISCOVER_AI_TOKEN`；不得把密钥提交进仓库。dev 使用本地模型，不用代理账户池。
3. 按 dev 配置仓的 `env/services/rediscover.json`、`env/running.json` 及 `env/services/web-gateway.json` 部署；Rediscover 使用 gateway 的独立前缀（旧 W 代理会记录响应头，不应用作 Rediscover 的会话链路）。通过 `~/miniconda3/bin/python3 ~/m/svc/svc.py start|stop|status rediscover` 操作。常规更新只更新不可变 tag 引用、重启 Rediscover 并核验入口版本和课程路由。若回退，保留 DB 与密钥，选已经采用签名会话、且经过核验的历史版本；首发时没有这样的前版，则仅撤 Rediscover 的 gateway 路由并停 Rediscover，不改其他应用路由。修改 gateway 配置才需要在无活跃连接的窗口重启 gateway。

语音在现有 HTTP 上使用系统录音/音频文件选择；浏览器支持捕获时会提供设备录音器，否则先用系统录音再选文件。这条路径不依赖网页麦克风权限，不调用浏览器厂商的远程转写。音频通过现有 Web 进程发到同机 Rediscover（HTTP 不是加密链路，只应在现有受控 dev 网络使用），在内存解码，不作文件持久化；转写进同一个输入框，可编辑，不自动提交。限 20 秒、2 MB。列式时可手改未准确识别的数字与括号。

## 可复跑检查

在 dev 使用 `~/miniconda3/bin/python3`（以下记作 `python3`）。样板预览用新目录 `scratch=$(mktemp -d /tmp/rediscover-local.XXXXXX)`，启动 `python3 -B -m rediscover.server --port 18871 --db "$scratch/state.sqlite"`，不要用线上端口、DB 或浏览器资料目录。测试已有本地模型时设 `REDISCOVER_SPEECH_MODEL` / `REDISCOVER_LOCAL_AI_MODEL`，需要的依赖目录也在临时进程环境中配置。

- `python3 -B checks/build.py [--course A03]`：地图覆盖、独立手稿、HTML/图、链接、结构与算式题配置；`--course` 可重复。A03 加 `--reading-standard` 检查至少两幅图或有独立用途的分图；合流后再对全集加该开关。这个结构检查不取代逐课人工审阅。`python3 -B checks/curriculum_samples.py` 检查每条主线的一项具体计算、图注和收束。
- `python3 -B checks/flow.py <入口>/rediscover/ --all [--auth-file <既有授权文件>]`：用 HTTP 逐步实走每课两种模式，同稿的正文、图和推导做一致性检查。用 `--course A03`（可重复）做单课检查；缺省或 `--pilot` 跑 A03 与兼容课 B01。
- `python3 -B checks/failure.py http://127.0.0.1:18871/rediscover/ "$scratch/state.sqlite" "$scratch"`：只在新建的独立测试目录和非线上端口故障注入。
- `python3 -B checks/browser.py <入口>/rediscover/ --chrome <已安装Chromium> --profile <新建于/tmp的短路径> --output <证据目录>`：需 `websocket-client`。线上加 `--auth-file`；AI 可用时加 `--ai`，实际语音验证加 `--audio <测试录音.wav>`。若测试机无中文系统字体，可加 `--fonts <本地 CJK 字体目录>`，只作用于该临时 Chromium 配置。浏览器通过真正 HTTP 运行脚本，桌面/手机视口有独立过程；不把截图或录音作为发布内容。配置鉴权文件参数只传路径，不打印文本。
