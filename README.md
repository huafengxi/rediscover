# rediscover

重走发现之路。阅读配图课文，从问题和失败的尝试出发，再用证据检验。可以连贯阅读，也可以切换到答题模式，在关键步骤自己预测、列式或解释。

## 项目内容

- [课程与关卡地图](docs/curriculum-map.md)涵盖 A–J 的 110 个专题关、K–M 的 18 个共享工具关和 N 的 12 个登月综合关。
- [教学引擎设计](docs/engine-design.md)定义两种模式、课文步骤、内容揭示、文字与语音作答及判题。
- [课程验收标准](docs/lesson-acceptance.md)定义阅读体验、配图、题面、计算、引导与发布检查。
- [项目背景](docs/project-context.md)记录学习目标、课程呈现和各条发现路线。
- [《火带走了什么？》主持稿](lessons/fire/host.md)是 B01 各证据卡和迁移题的改编依据。
- [`courses/`](courses/) 是 140 篇独立的 Markdown 手稿。A03 是双模式阅读样板，参见[作者说明](docs/release.md#内容与判定)。手稿、未展开证据和判据不作为静态资源发布。

## 本地运行

```sh
py="$HOME/miniconda3/bin/python3"
"$py" -B checks/build.py
scratch=$(mktemp -d /tmp/rediscover-local.XXXXXX)
"$py" -B -m rediscover.server --port 18871 --db "$scratch/state.sqlite"
```

打开 [课程目录](http://127.0.0.1:18871/rediscover/)、[A03 阅读](http://127.0.0.1:18871/rediscover/A03/)或 [A03 答题](http://127.0.0.1:18871/rediscover/A03/?mode=quiz)。在另一终端用同一 Python 运行 `checks/flow.py http://127.0.0.1:18871/rediscover/ --course A03`；改用 `--all` 可检查全部课程的两种模式。默认不加载可选模型，解释题仍可查看作者解释；数学不依赖模型。部署、运行数据与检查方法见 [发布手册](docs/release.md)。
