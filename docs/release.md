# Rediscover 发布手册

课程入口 `/rediscover/`；每个课程在 `/rediscover/<ID>/`。`/rediscover/health` 返回运行版本、课程数和推理能力。服务只绑定 loopback；从 dev Web 入口访问时沿用原有 BasicAuth。不要把应用直连端口暴露到网络。

## 内容与判定

`courses/<ID>.md` 中每个 `@@` 开始一个步骤，后跟单行 JSON 配置，再跟 Markdown 正文（段落、三级标题、引用、强调、代码及课程/HTTPS 链接）。标题与任务取课程地图。`figure` 是独立配图的作者数据（示意节点、时间折线、条形、对照图或等分带），同时给图注与替代文字；服务器仅在该步展开后提供对应 SVG。新题先在 `checks/build.py` 通过编译；表达式示例和答案只在服务端，解释判据及解决过程用独立字段。若修改步骤次序、ID 或判题意义，提高该课 `version`，以免旧进度误套到新的证据序列。

`continue`、`submit`、`skip` 和 `reveal` 各由 SQLite 事务记为一次动作，保存后返回开放区。表达式解析只接受有限数字算术语法，以分数精确计算，允许作者设置容差、部分结果和所需原始数据，不执行表达式代码。答案进入进度 DB；没有发送答案或凭据的遥测。

## dev 发布

1. 构建通过后把 commit 及唯一 `deploy-*` tag 推到项目 `origin`。在 `~/m/run/local/data/rediscover/releases/<tag>/` 装配该 tag（例如新建目录后 `git archive <tag> | tar -x -C <release>`），部署快照不由日常工作树运行。
2. 把状态单独放在 `~/m/run/local/data/rediscover/state/`（含 SQLite、WAL）；依赖与模型也在发布目录之外。`requirements-dev-service.txt` 用单独的 `--system-site-packages` venv 装配；PyTorch、Transformers 使用 dev 既有 Python 运行时。可选 `REDISCOVER_SPEECH_MODEL` 指向已下载的 Vosk Small CN 目录，可选 `REDISCOVER_LOCAL_AI_MODEL` 指向已校验的本地 Qwen 模型目录。加载只读、本地、无自动下载、禁用远程模型代码。输出只作为当前步的有限判据标签；给读者的反馈来自作者，读者可随时直接展开作者解释。只有显式授权使用 OpenAI 兼容适配器的部署才配置 `REDISCOVER_AI_URL`、`REDISCOVER_AI_MODEL` 及从既有授权配置注入的 `REDISCOVER_AI_TOKEN`；不得把密钥提交进仓库。dev 使用本地模型，不用代理账户池。
3. 按 dev 配置仓的 `env/services/rediscover.json`、`env/running.json` 和对应 Web 路由部署；通过 `~/miniconda3/bin/python3 ~/m/svc/svc.py start|stop|status rediscover` 操作。新发布需更新不可变 tag 引用、重启 Rediscover 并核验入口版本以及课程路由。回退保留 DB，先把声明的版本和目录切回此前可用 tag，再重启 Rediscover；首发前无 Rediscover 发布，首发回退是撤 Rediscover 路由并停 Rediscover，其他站点无需停。

语音在现有 HTTP 上使用系统录音/音频文件选择；浏览器支持捕获时会提供设备录音器，否则先用系统录音再选文件。这条路径不依赖网页麦克风权限，不调用浏览器厂商的远程转写。音频通过现有 Web 进程发到同机 Rediscover（HTTP 不是加密链路，只应在现有受控 dev 网络使用），在内存解码，不作文件持久化；转写进同一个输入框，可编辑，不自动提交。限 20 秒、2 MB。列式时可手改未准确识别的数字与括号。

## 可复跑检查

- `python3 -B checks/build.py`：地图覆盖、独立手稿、HTML/图、链接、结构与算式题配置。
- `python3 -B checks/flow.py <入口>/rediscover/ --all [--auth-file <既有授权文件>]`：独立 HTTP 检查（包括提前读取和重复动作），逐步加载每一课和配图。
- `python3 -B checks/failure.py http://127.0.0.1:18871/rediscover/ "$scratch/state.sqlite" "$scratch"`：只在新建的独立测试目录和非线上端口故障注入。
- `python3 -B checks/browser.py <入口>/rediscover/ --chrome <已安装Chromium> --profile <新建于/tmp的短路径> --output <证据目录>`：需 `websocket-client`。线上加 `--auth-file`；AI 可用时加 `--ai`，实际语音验证加 `--audio <测试录音.wav>`。浏览器通过真正 HTTP 运行脚本，桌面/手机视口有独立过程；不把截图或录音作为发布内容。配置鉴权文件参数只传路径，不打印文本。
