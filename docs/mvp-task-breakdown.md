# MVP 范围定义与开发任务拆分

> 版本：v1.0
> 日期：2026-11-03
> 基线：commit `c828263`
> 关联：`docs/architecture-frontend-backend-separation.md`、`docs/api-v1-reference.md`、`docs/prd-junior-vocabulary-dictation-v0.2.md`

---

## 0. MVP 范围：先把边界钉死

MVP 唯一目标：**让孩子能完成一次完整的「选范围 → 默写 → 看结果 → 只练错词 → 明天接着练」闭环，并且进度不丢。**

这一个闭环跑通，产品就成立。跑不通，加再多题型都是零。

### 0.1 做什么（In Scope）

| 能力 | 具体到页面 |
|---|---|
| 选范围与题型 | 单元 / 主题 / 错词本；汉译英 + 听音写词 |
| 答题与判题 | 逐字符差异高亮、拼写接近提示、提示后答对单独计数 |
| 结果页 | 正确率、首答正确率、错题清单 |
| 只练错词 | 一键从结果页重开错词专项 |
| 错词本 | 到期优先排序、今日待复习角标 |
| 进度持久化 | 按 `(learner, word, skill)` 存盒子等级与下次复习时间 |
| 发音 | 英/美音播放，三层降级到设备语音 |
| 词库 | 内置种子词库（人教版一个年级），支持搜索筛选 |

### 0.2 不做什么（Out of Scope，写清楚是为了防止范围蔓延）

| 不做 | 原因 | 什么时候做 |
|---|---|---|
| PDF 导入 | 占 MVP 一半以上工作量，且准确率不确定 | v0.3.0 |
| 英译汉 / 音标写词 | 判题规则已设计好，但会稀释联调精力 | v0.3.0 |
| 账号登录 / 多设备同步 | 单机自用，`learner_id` 够用 | 有第二台设备需求时 |
| 家长端报表 | 先有数据再谈报表 | v1.0 之后 |
| AI 生成题目 / AI 讲解 | 判题必须确定性，AI 只做辅助 | 长期 |
| 打印 / 导出 PDF 练习卷 | 与核心闭环无关 | 待定 |
| 微信小程序 / 移动 App | Web 响应式已够 | 待定 |
| 云端部署 | 先本机跑通 | v1.0 之后 |

### 0.3 唯一硬性外部依赖

**种子词库**。没有词就没有产品。这也是唯一需要你拍板的输入（教材版本）。

---

## 1. 里程碑与版本号

| 里程碑 | 内容 | Tag | 判定标准 |
|---|---|---|---|
| M0 基线 | 端口统一、应用工厂、旧功能契约测试、无回归 | `v0.0.1` | 7 条兼容红线全绿 |
| M1 骨架 | 数据层 + API 骨架 + 前端工程可跑 | `v0.1.0` | 前端能调到 `GET /api/v1/health` 并展示词库列表 |
| M2 闭环 | 练习全链路 + 错词本 + 发音 | `v0.2.0` | 能完整走完一次 20 题默写并看到错词 |
| M3 增强 | PDF 导入 + 其余题型 + 统计 | `v0.3.0` | 上传一份 PDF 能导入 100+ 词 |
| M4 稳定 | 测试覆盖、可访问性、部署文档 | `v1.0.0` | `pytest` 全绿，移动端可用 |

**M2 是真正的交付线。** M0/M1 只是为它铺路。

---

## 2. Epic 总览

| Epic | 名称 | 任务数 | 预估 | 里程碑 |
|---|---|---|---|---|
| E0 | 工程基线整治 | 5 | 1.5 天 | M0 |
| E1 | 数据层 | 6 | 3 天 | M1 |
| E2 | API 骨架 | 5 | 2 天 | M1 |
| E3 | 词库 API | 4 | 1.5 天 | M1 |
| E4 | 练习与判题 | 7 | 4 天 | M2 |
| E5 | 错词本与进度 | 4 | 1.5 天 | M2 |
| E6 | 发音 | 4 | 1.5 天 | M2 |
| E7 | 前端工程与设计系统 | 5 | 2.5 天 | M1 |
| E8 | 前端页面 | 8 | 5 天 | M2 |
| E9 | 联调、测试、上线 | 5 | 2.5 天 | M2 |
| **合计** | | **53** | **约 25 人天** | |

> 按每天投入 2-3 小时估算，M2 大约需要 **4-6 周**。这个估算包含调试和返工，不是纯写代码时间。

---

## 3. 详细任务清单

### E0 工程基线整治（1.5 天，必须先做）

| ID | 任务 | 模块 | 依赖 | 交付物 | 验收标准 | 估时 |
|---|---|---|---|---|---|---|
| T0-1 | 统一端口配置 | `app.py` `config.py` | — | `PORT` / `POSTER_BASE_URL` 读环境变量 | 改 `PORT=5050` 后，页面能开、**PNG 导出也成功**（这是双硬编码的验证点） | 0.3 |
| T0-2 | 抽 `create_app()` 应用工厂 | `app.py` | T0-1 | 工厂函数 + 模块级 `app` | `gunicorn app:app` 仍能启动；`pytest` 能创建独立实例 | 0.4 |
| T0-3 | 补 `.gitignore` 与构建产物隔离 | `.gitignore` | — | 忽略 `data/` `static/spa/` `*.mp3` 等 | `git status` 在构建后仍干净 | 0.1 |
| T0-4 | 编写旧功能契约测试 | `tests/test_legacy_contract.py` | T0-2 | 7 条红线的断言 | 改造前后均全绿；故意改坏一条能被测出 | 0.5 |
| T0-5 | 修掉异常泄露与缺失校验 | `app.py` | T0-2 | 固定错误文案 | `/api/generate` 传空参数返回 400 且不含堆栈 | 0.2 |

> **T0-4 是整个项目最有价值的一小时。** 它把「我没改坏旧功能」从感觉变成事实。

---

### E1 数据层（3 天）

| ID | 任务 | 模块 | 依赖 | 交付物 | 验收标准 | 估时 |
|---|---|---|---|---|---|---|
| T1-1 | ORM 模型定义 | `core/models.py` | T0-2 | 7 张表：`Learner` `Word` `WordSense` `Unit` `SkillProgress` `PracticeSession` `PracticeItem` | `Base.metadata.create_all()` 能建全表；外键与索引齐全 | 0.8 |
| T1-2 | 数据库连接与 WAL | `core/db.py` | T1-1 | engine + Session | 并发读写不报 `database is locked` | 0.3 |
| T1-3 | Alembic 初始化 | `alembic/` | T1-1 | 首个迁移脚本 | `alembic upgrade head` 能从空库建到最新；`downgrade` 可回退 | 0.5 |
| T1-4 | 种子词库导入 | `core/seed.py` `data/seed/words.csv` | T1-2 | 命令行 `python -m core.seed` | 导入后 `/api/v1/health` 的 `words_count > 0`；重复执行不产生重复数据（幂等） | 0.8 |
| T1-5 | 间隔重复调度 | `core/srs.py` | T1-1 | `next_box()` / `next_review_at()` | 单测覆盖 5 个盒子升降级 + 毕业；答错必回盒 1 | 0.4 |
| T1-6 | 文本规范化 | `core/normalize.py` | — | `normalize_en()` / `normalize_zh()` | 全角字母、弯引号、多空格、大小写全部覆盖；中文去标点但英文保留撇号 | 0.2 |

**T1-4 的前置输入**：教材版本 + 词表来源。这是唯一的外部阻塞项。若词表还没定，先用 50 个手写词打通链路（`data/seed/words.sample.csv`），不阻塞后续开发。

**表结构要点**

```
Learner(learner_id PK, nickname, settings_json, created_at)
Unit(unit_id PK, unit_name, book, order_no)
Word(word_id PK, form, phonetic_uk, phonetic_us, pos, unit_id FK, theme, created_at)
WordSense(sense_id PK, word_id FK, meaning_cn, accepted_json, example_en, example_cn, order_no)
SkillProgress(id PK, learner_id FK, word_id FK, sense_id FK, skill,
              box, status, correct_count, wrong_count,
              next_review_at, last_wrong_at)
              -- UNIQUE(learner_id, word_id, sense_id, skill)
PracticeSession(session_id PK, learner_id FK, mode, range, range_value,
                order_, hint_enabled, size, status, created_at, expires_at)
PracticeItem(item_id PK, session_id FK, index_no, word_id FK, sense_id FK,
             hint, answered, answer_raw, correct, hint_used,
             elapsed_ms, answered_at)
```

---

### E2 API 骨架（2 天）

| ID | 任务 | 模块 | 依赖 | 交付物 | 验收标准 | 估时 |
|---|---|---|---|---|---|---|
| T2-1 | 创建 `/api/v1` 蓝图 | `api/v1/__init__.py` | T0-2 | 蓝图 + 注册 | `GET /api/v1/health` 返回 200 | 0.3 |
| T2-2 | 统一错误处理 | `api/v1/errors.py` | T2-1 | 4 个错误处理器 | 抛 `ApiError` 得到规范 body；未捕获异常返 500 且**不含堆栈** | 0.5 |
| T2-3 | 请求校验层 | `api/v1/schemas.py` | T2-1 | pydantic 模型 + 装饰器 | 非法参数返 400 且 `details` 能定位到字段 | 0.5 |
| T2-4 | 分页与响应工具 | `api/v1/utils.py` | T2-1 | `paginate()` / `ok()` | 三个列表接口复用同一套分页结构 | 0.4 |
| T2-5 | 请求日志与 trace id | `app.py` | T2-1 | `before_request` 钩子 | 每个响应头带 `X-Request-Id`，日志能对上 | 0.3 |

---

### E3 词库 API（1.5 天）

| ID | 任务 | 模块 | 依赖 | 交付物 | 验收标准 | 估时 |
|---|---|---|---|---|---|---|
| T3-1 | 单元 / 主题列表 | `api/v1/words.py` | T2-2 T1-2 | 2 个 GET | 每单元 `word_count` 与数据库实际条数一致（**不能硬编码**） | 0.3 |
| T3-2 | 单词列表（搜索+筛选+分页） | `api/v1/words.py` | T3-1 | `GET /words` | `q` 同时匹配词形与中文；`status` 多值可用；分页 `total` 正确 | 0.6 |
| T3-3 | 单词详情 | `api/v1/words.py` | T3-2 | `GET /words/{id}` | 返回全部义项 + `progress_by_skill` | 0.3 |
| T3-4 | 学习者档案与统计 | `api/v1/stats.py` | T2-2 | 2 个 GET | 今日 `done`/`accuracy` 与当日作答记录一致 | 0.3 |

---

### E4 练习与判题（4 天，本 Epic 是核心）

| ID | 任务 | 模块 | 依赖 | 交付物 | 验收标准 | 估时 |
|---|---|---|---|---|---|---|
| T4-1 | 判题核心（纯函数） | `core/grading.py` | T1-6 | `grade(answer, expected, mode)` | **单测 ≥ 20 条**：大小写、多空格、全角、撇号、漏字母、多字母、错字母、空输入、中文同义词 | 1.2 |
| T4-2 | 逐字符 diff 生成 | `core/grading.py` | T4-1 | `build_diff()` | `environment` vs `enviroment` 能准确标出 `missing` 位置 | 0.5 |
| T4-3 | 抽题逻辑 | `api/v1/practice.py` | T3-2 T1-5 | `draw_items()` | 三种 `order` 正确；池子不足时返回 `size` 为实际数 + `warnings` | 0.8 |
| T4-4 | 创建会话接口 | `api/v1/practice.py` | T4-3 | `POST /sessions` | 返回题目不含答案；`hint` 按 `hint_enabled` 决定是否下发 | 0.5 |
| T4-5 | 提交答案接口 | `api/v1/practice.py` | T4-1 T4-4 | `POST /answers` | 答错返 200；`first_try_correct` 在 `hint_used=true` 时必为 false；重复提交不重复计数 | 0.6 |
| T4-6 | 结束会话接口 | `api/v1/practice.py` | T4-5 | `POST /finish` | 汇总数字自洽（`correct+wrong==answered`）；幂等，重复调用不重复写错词本 | 0.4 |
| T4-7 | 会话过期与状态机 | `api/v1/practice.py` | T4-4 | 状态校验 | 过期返 `409 SESSION_EXPIRED`；已结束返 `409 SESSION_FINISHED` | 0.2 |

> **T4-1 建议先写测试再写实现。** 判题规则一旦写错，后面所有统计都是错的，而且错得很隐蔽——用户只会觉得"系统判错了"，不会报 bug。

---

### E5 错词本与进度（1.5 天）

| ID | 任务 | 模块 | 依赖 | 交付物 | 验收标准 | 估时 |
|---|---|---|---|---|---|---|
| T5-1 | 错词本查询 | `api/v1/wrongbook.py` | T4-6 | `GET /wrongbook` | 到期优先排序正确；`is_due` 与 `next_review_at` 一致 | 0.6 |
| T5-2 | 手动标记掌握/重置 | `api/v1/wrongbook.py` | T5-1 | `PATCH /{word_id}` | `master` 后不再出现在默认列表；`reset` 后回盒 1 | 0.4 |
| T5-3 | 按技能分离进度验证 | `core/srs.py` | T5-1 | 测试用例 | 同一个词 `zh_to_en` 答对、`audio_to_en` 仍为 `new` | 0.3 |
| T5-4 | 今日待复习统计 | `api/v1/stats.py` | T5-1 | 汇总字段 | 侧边栏角标数与列表 `due_today` 一致 | 0.2 |

---

### E6 发音（1.5 天）

| ID | 任务 | 模块 | 依赖 | 交付物 | 验收标准 | 估时 |
|---|---|---|---|---|---|---|
| T6-1 | 音频缓存与 manifest | `core/audio.py` | T1-2 | 文件布局 + `manifest.json` | 同名请求第二次命中缓存（响应头 `X-Audio-Source: cache`） | 0.4 |
| T6-2 | Piper 本地合成 provider | `core/audio.py` | T6-1 | `PiperProvider` | 给定词形能产出 mp3；**逐 voice 记录 MODEL_CARD** | 0.6 |
| T6-3 | 发音接口 | `api/v1/audio.py` | T6-1 | `GET /audio/{id}` | 返回 `audio/mpeg` + `Cache-Control: immutable`；失败返 404 `AUDIO_NOT_AVAILABLE` | 0.3 |
| T6-4 | 全链失败的降级约定 | 前后端 | T6-3 | 约定文档 + 前端逻辑 | 404 时前端**不弹全局错**，切设备语音并标注"演示" | 0.2 |

---

### E7 前端工程与设计系统（2.5 天）

| ID | 任务 | 模块 | 依赖 | 交付物 | 验收标准 | 估时 |
|---|---|---|---|---|---|---|
| T7-1 | Vite + Vue3 工程搭建 | `frontend/` | — | `package.json` / `vite.config.js` | `npm run dev` 能起；`base:'/app/'`；`proxy /api → :5000` | 0.5 |
| T7-2 | 设计 token 迁移 | `src/styles/tokens.css` | T7-1 | CSS 变量 | 颜色/字体/间距/圆角与 `prototype/styles.css` 一致 | 0.4 |
| T7-3 | 基础组件（8 个） | `src/components/` | T7-2 | Button/Input/Card/Chip/Dialog/Toast/ProgressBar/EmptyState | 全部支持键盘操作；触控目标 ≥44px | 0.8 |
| T7-4 | axios 客户端与拦截器 | `src/api/client.js` | T7-1 | 统一错误处理 | 4xx 走字段提示，5xx 展示 `request_id`；`AUDIO_NOT_AVAILABLE` 白名单不弹错 | 0.3 |
| T7-5 | Pinia store 骨架 | `src/stores/` | T7-4 | 4 个 store | 状态可持久化 `learner_id` 到 `localStorage` | 0.5 |

---

### E8 前端页面（5 天）

| ID | 任务 | 对应原型 | 依赖 | 验收标准 | 估时 |
|---|---|---|---|---|---|
| T8-1 | 应用外壳 + 路由 + 移动端导航 | 侧边栏/topbar/底部导航 | T7-5 | 8 个路由可达；≤860px 出底部导航；无横向滚动 | 0.7 |
| T8-2 | 学习首页 | `#view-dashboard` | T8-1 T3-4 | 数字卡片来自接口，非硬编码 | 0.5 |
| T8-3 | 单词库页 | `#view-words` | T8-1 T3-2 | 搜索防抖 300ms；筛选与分页联动；空态有引导 | 0.8 |
| T8-4 | 默写设置页 | `#view-config` | T8-1 T3-1 | 范围胶囊显示**接口返回**的词数；摘要实时联动 | 0.7 |
| T8-5 | 答题页 | `#view-practice` | T8-4 T4-5 | 逐字符 diff 渲染正确；提示后答对文案区分；Enter 提交/下一题 | 1.0 |
| T8-6 | 结果页 | `#view-result` | T8-5 T4-6 | 首答正确率单独展示；「只练本次错词」能重开会话 | 0.5 |
| T8-7 | 错词本页 | `#view-wrong` | T8-1 T5-1 | 到期分组；角标与列表一致 | 0.5 |
| T8-8 | 设置页 + 旧版入口 | `#view-settings` | T8-1 | 口音/提示开关可改并持久化；旧版跳 `/` | 0.3 |

> 原型的 HTML/CSS 可作为**视觉基准**直接参考，但逻辑要重写为 Vue 组件——不要把 `prototype/app.js` 的 DOM 操作搬进 Vue。

---

### E9 联调、测试、上线（2.5 天）

| ID | 任务 | 依赖 | 验收标准 | 估时 |
|---|---|---|---|---|
| T9-1 | 后端接口测试 | E2-E6 | `pytest` 覆盖核心路径，判题单测 ≥20 条 | 0.8 |
| T9-2 | Playwright E2E 主链路 | T8-5 | 用 `data-testid` 走完 登录→选题→答题→结果→重练 | 0.7 |
| T9-3 | 移动端与可访问性 | T8-* | 390px 无溢出；键盘可操作；对比度 ≥4.5:1 | 0.4 |
| T9-4 | 生产构建与 SPA 兜底验证 | T7-1 | `npm run build` 后访问 `/app/` 与 `/app/words` 均正常；**旧路由仍正常** | 0.4 |
| T9-5 | 更新 README 与启动说明 | 全部 | 新人能按文档从零跑起来 | 0.2 |

---

## 4. Sprint 排期

按每周一个 Sprint、每 Sprint 投入 5-6 小时估算：

| Sprint | 任务 | 产出 | 可演示的东西 |
|---|---|---|---|
| **S1** | T0-1 ~ T0-5、T1-1 ~ T1-3 | 工程基线 + 空数据库 | `pytest` 全绿，旧功能零回归 |
| **S2** | T1-4 ~ T1-6、T2-1 ~ T2-5、T3-1 ~ T3-4 | 数据 + API 骨架 + 词库 API | `curl` 能查词组 |
| **S3** | T4-1 ~ T4-2（判题）、T7-1 ~ T7-5 | 判题核心 + 前端工程 | 前端能列表展示词库 ← **M1 达成 `v0.1.0`** |
| **S4** | T4-3 ~ T4-7、T5-1 ~ T5-4 | 练习全链路 | `curl` 能建会话、答题、看结果 |
| **S5** | T8-1 ~ T8-5 | 答题界面 | **能真的在浏览器里默写** |
| **S6** | T8-6 ~ T8-8、T6-1 ~ T6-4、T9-1 ~ T9-5 | 结果/错词/发音/测试 | 完整闭环 ← **M2 达成 `v0.2.0`** |

**S5 结束是成就感的峰值**——第一次能真的默写。建议把 S5 的验收当成阶段性庆祝点，不要等到 S6。

---

## 5. 关键路径与阻塞项

```
T0-1 端口统一 ──► T0-2 应用工厂 ──┬──► T2-1 API 蓝图 ──► T3-* ──► T4-* ──► T5-* ──► T9
                                  ├──► T1-1 ORM ──► T1-2 ──► T1-4 种子词库
                                  └──► T0-4 契约测试（守住旧功能）

T7-1 前端工程 ──► T7-2 ──► T7-3 ──► T8-1 ──► T8-4 ──► T8-5（最长前端链）
```

**三个真实阻塞点**

| 阻塞 | 卡住什么 | 解除办法 |
|---|---|---|
| **教材版本未定** | T1-4 种子词库 → 卡住 T4-3 抽题 → 卡住整个 E4 | 先用 50 个手写词构建 `words.sample.csv`，链路照跑，词表后换 |
| **判题规则未确认**（中文同义词策略） | T4-1 | 先按 `accepted` 数组实现，语义争议留到有真实错例再调 |
| **Piper 环境未验证**（Python 依赖 + 模型下载） | T6-2 | 提前半天做技术验证；失败则首发直接降级到浏览器 TTS，接口不变 |

---

## 6. Definition of Done

每个任务完成的判定，不只是"代码写完"：

- [ ] 代码合并到 `main`，`git log` 有一条独立提交
- [ ] 有对应的测试，且 `pytest` 全绿
- [ ] 接口改动同步更新 `docs/api-v1-reference.md`
- [ ] 7 条兼容红线仍然全绿（`tests/test_legacy_contract.py`）
- [ ] 前端改动在 390px 与 1440px 两个宽度下都验证过
- [ ] 涉及用户可见文案的，是中文且说人话（不出现 `VALIDATION_ERROR` 这种裸错误码）

**Sprint 级 DoD 额外两条**：
- 打 tag 并推送（`git push origin v0.x.0`）
- 在 `docs/` 里留一条本次改动的说明，哪怕是三行

---

## 7. 风险登记

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| 词表版权不清 | 中 | 高（不能发布） | 只用 ECDICT（MIT）+ 自建映射；商用词表一律不打包 |
| 判题规则返工 | 中 | 中 | 先写测试；`accepted` 数组可配置，不改代码就能加同义写法 |
| PDF 解析（P1）低估 | 高 | 中 | 已明确不属 MVP；真做时按"解析→复核→发布"三段独立验收 |
| 前端重写偏离原型视觉 | 中 | 低 | 原型作为视觉基准，样式 token 直接迁 |
| 一个人做导致半途停滞 | 中 | 高 | 每个 Sprint 都有可演示产出，避免"做了三周看不到东西" |

---

## 8. 现在就能开工的 5 件事（按顺序）

1. **T0-1 端口统一** —— 半天，风险最低，收益立现（PNG 导出不再随机失败）
2. **T0-4 契约测试** —— 一小时，为后面所有改造上保险
3. **T0-2 应用工厂** —— 为蓝图提供挂载点
4. **T1-1 ORM 模型** —— 数据模型定了，后面接口才有形状
5. **T7-1 Vite 工程** —— 与后端并行，互不阻塞

前两件加起来**不到一天**，但能把整个项目的安全垫铺好。

---

## 9. 需要你拍板的三个问题

| # | 问题 | 影响 | 默认建议 |
|---|---|---|---|
| Q1 | 首版教材版本？人教版 / 外研版 / 译林版 | 决定 T1-4 词表来源，阻塞 E4 | 人教版 |
| Q2 | 孩子现在几年级？ | 决定首版词库覆盖哪个册次 | 若为初一，先做七年级上下册 |
| Q3 | 中文题同义写法要不要人工维护？ | 决定 T4-1 判题复杂度 | 要，先维护 100 个高频词的 `accepted` |

这三个定了，S1 就能直接开工。
