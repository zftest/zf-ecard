# 整体技术架构方案：保留旧方案，新增功能前后端分离

> 版本：v1.0
> 日期：2026-11-03
> 适用代码基线：commit `c828263`（首次导入）
> 关联文档：`docs/api-v1-reference.md`、`docs/mvp-task-breakdown.md`、`docs/prd-junior-vocabulary-dictation-v0.2.md`

---

## 0. 一页结论

| # | 结论 | 关键理由 |
|---|---|---|
| 1 | **不引入第二个后端进程**。仍然只有 Flask 一个服务，同时承载「旧 Jinja 页面 + 新 `/api/v1` + Vue SPA 静态资源」 | 引入 FastAPI 意味着两个进程、两套部署、两套日志、跨进程共享 SQLite 写锁。收益只是"技术栈更现代"，代价是运维复杂度翻倍。这个项目是单机自用，不值 |
| 2 | **旧路由原地不动**。第一阶段不把 `app.py` 里的 7 个路由搬进 Blueprint | `url_for("show_poster")` 是**运行期**才解析的。一旦搬进 Blueprint，endpoint 会变成 `legacy.show_poster`，旧代码里的 `url_for` 不会报错在改代码时，而是在用户点"生成"时才抛 `BuildError` → 500。这是最典型的"重构引入静默回归" |
| 3 | **Vue SPA 挂载在 `/app/` 前缀下**，不与旧路径竞争 | 旧路由占了 `/`、`/poster/*`、`/poster-demo/*`、`/loading`、`/api/*`。SPA 必须拿一个专属前缀，否则 history 模式的 catch-all 会把旧页面全部吃掉 |
| 4 | **开发期靠 Vite proxy，生产期靠 Flask 静态托管，全程不需要 CORS** | 同源是省掉一整套 CORS 配置、预检请求、Cookie 策略的最便宜办法 |
| 5 | **判题逻辑做成纯函数模块**，与 Flask、数据库完全解耦 | 判题是这个产品最容易出错、最需要反复回归的部分，必须能脱离 Web 层单测 |
| 6 | **旧的文件缓存（`output/cache/*.json`）保留不动，新数据走 SQLite** | 两套存储各管各的，互不迁移。避免"顺手统一存储"把旧功能搞坏 |

---

## 1. 现状盘点（基于真实代码，非推测）

### 1.1 现有结构

```
knowledge-card-generato-main/
├── app.py                      # 408 行，全部路由 + 两个 HTML 格式化函数
├── config.py                   # 真实密钥，已 gitignore，不入库
├── config.example.py           # 模板，入库
├── services/
│   ├── deepseek_client.py      # 调 DeepSeek，返回 {meta, cards}
│   └── poster_exporter.py      # Playwright 截图
├── templates/                  # 5 个 Jinja 模板
├── static/css|js               # main.css / poster.css / main.js
├── prompts/                    # 分学科 prompt 文本
├── output/cache/*.json         # 文件缓存（gitignore）
├── prototype/                  # 纯静态 UI 原型（已入库）
└── docs/                       # 文档
```

### 1.2 现有路由清单（7 个，全部在 `app.py`）

| # | 路径 | 方法 | 类型 | endpoint 名 |
|---|---|---|---|---|
| 1 | `/` | GET | Jinja 页面 | `index` |
| 2 | `/api/generate` | POST | JSON API | `api_generate` |
| 3 | `/generate` | POST | 表单 → 302 | `generate_poster_form` |
| 4 | `/poster/<poster_id>` | GET | Jinja 页面 | `show_poster` |
| 5 | `/poster-demo/<poster_id>` | GET | Jinja 页面 | `show_poster_demo` |
| 6 | `/api/export/<poster_id>` | GET | 文件下载 | `api_export` |
| 7 | `/loading` | GET | Jinja 页面 | `loading` |

### 1.3 四个必须先处理的技术债

| 债务 | 位置 | 影响 | 处理时机 |
|---|---|---|---|
| **端口双硬编码** | `app.py:383` 拼 `http://127.0.0.1:5000/...`；`app.py:407` `port=5000` | 改了一个没改另一个 → **PNG 导出一律失败**，且报错信息会误导（看起来像 Playwright 问题，实际是 URL 打到了错误端口） | Sprint 1 第一件事 |
| **模块级 `app = Flask(__name__)`，无应用工厂** | `app.py:21` | 无法在测试里创建隔离实例；`create_app()` 缺失导致蓝图注册无处安放 | Sprint 1 |
| **原始异常直接回传给前端** | `app.py:303` `f"AI 生成失败：{str(e)}"` | 泄露文件路径、库版本、甚至密钥片段 | Sprint 1 顺手修 |
| **无输入校验** | `app.py:288-297` 只判断非空 | 超长字符串直接打进 prompt，可能撑爆 token 或注入 | Sprint 1 顺手修 |

---

## 2. 目标架构

### 2.1 目录结构（新增部分用 `+` 标注）

```
knowledge-card-generato-main/
├── app.py                          # 改造：加 create_app()，旧路由原地保留
├── config.py                       # 新增 PORT / DATABASE_URL / POSTER_BASE_URL（不入库）
├── config.example.py               # 同步补字段（入库）
│
├── api/                            # + 新增：新 API 全部在这里
│   ├── __init__.py                 # +
│   └── v1/
│       ├── __init__.py             # + Blueprint("api_v1", url_prefix="/api/v1")
│       ├── errors.py               # + 统一错误类型与错误处理器
│       ├── schemas.py              # + 请求/响应模型（pydantic v2）
│       ├── words.py                # + 词库查询
│       ├── practice.py             # + 练习会话与判题
│       ├── wrongbook.py            # + 错词本
│       ├── audio.py                # + 发音
│       ├── imports.py              # + PDF 导入
│       └── stats.py                # + 统计
│
├── core/                           # + 新增：领域逻辑，不依赖 Flask
│   ├── __init__.py                 # +
│   ├── db.py                       # + SQLAlchemy engine / session
│   ├── models.py                   # + ORM 实体
│   ├── grading.py                  # + 判题纯函数（重点单测对象）
│   ├── srs.py                      # + 间隔重复调度
│   ├── audio.py                    # + 发音 provider 链与缓存
│   ├── normalize.py                # + 文本规范化
│   └── seed.py                     # + 首次启动灌词库 + 默认 learner
│
├── frontend/                       # + 新增：Vue3 SPA 源码
│   ├── package.json                # +
│   ├── vite.config.js              # + base:"/app/", proxy /api/v1 → 5000
│   ├── index.html                  # +
│   └── src/
│       ├── main.js                 # +
│       ├── App.vue                 # +
│       ├── router/index.js         # + createWebHistory('/app/')
│       ├── api/{client.js,words.js,practice.js,wrongbook.js,imports.js}  # +
│       ├── stores/{learner.js,words.js,practice.js,wrongbook.js}         # +
│       ├── styles/{tokens.css,base.css}                                   # + 迁自 prototype/
│       ├── components/             # + 8 个基础组件
│       └── views/                  # + 8 个页面（对应 prototype 8 视图）
│
├── static/spa/                     # + 构建产物（gitignore）
├── data/                           # + ecard.db / audio/ / seed/（gitignore）
└── tests/                          # + pytest
```

### 2.2 运行时形态

**开发期（两个端口，一个来源）**

```
浏览器 :5173
  │
  ├─ /app/*          → Vite Dev Server（HMR 热更新）
  └─ /api/v1/*       → Vite proxy 转发 → Flask :5000
                                          │
                                          └─ /api/generate 等旧接口也一并代理
```

- 前端 `npm run dev`，后端 `.venv/Scripts/python.exe app.py`
- **关键**：`vite.config.js` 里 `server.proxy['/api']` 指向 `http://127.0.0.1:5000`，浏览器视角只有一个 origin → **零 CORS 配置**

**生产期（单进程单端口）**

```
浏览器 :5000
  │
  └─ Flask :5000
       ├─ /                    → Jinja 旧首页
       ├─ /poster/<id>         → Jinja 旧海报页（不变）
       ├─ /api/generate        → 旧 JSON API（冻结，不再改）
       ├─ /api/v1/*            → 新 REST API
       └─ /app/*               → static/spa 静态文件 + history fallback
```

- 前端 `npm run build` → 产物落在 `static/spa/`
- 后端单进程托管，无需 Nginx、无需 Node 运行时

### 2.3 为什么这样切分是"真分离"

"前后端分离"不是指"两个进程"，而是指**职责与契约分离**：

| 维度 | 分离前 | 分离后 |
|---|---|---|
| 页面渲染 | Flask `render_template` 拼 HTML | Vue 在浏览器渲染，Flask 只出 JSON |
| 数据契约 | 无契约，模板直接读 `data` 字典 | `/api/v1` 契约化，有 schema、有版本号 |
| 前端构建 | 无 | Vite，有 `npm run build`、有产物 |
| 开发并行 | 改模板要重启 Flask | Vite HMR，前端改样式不碰后端 |
| 可测试性 | 只能端到端点页面 | 后端 pytest 单测 + 前端组件测试 |
| 旧功能影响 | — | **零**，旧路由与模板完全不进入新链路 |

**旧功能不进新链路**这一条是硬约束：`templates/`、`static/css/poster.css`、`services/deepseek_client.py`、`output/cache/` 在本次架构中**一行都不改**。

---

## 3. 后端设计

### 3.1 应用工厂与蓝图注册（`app.py` 改造要点）

```python
# app.py 改造示意 —— 旧路由全部原地保留，只加壳

def create_app(config_object=None):
    app = Flask(__name__)
    app.secret_key = SECRET_KEY
    app.config.update(
        JSON_AS_ASCII=False,
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,   # PDF 上传上限 20MB
        DATABASE_URL=os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}"),
        POSTER_BASE_URL=os.getenv("POSTER_BASE_URL", f"http://127.0.0.1:{PORT}"),
    )
    if config_object:
        app.config.update(config_object)

    from api.v1 import bp as api_v1_bp
    app.register_blueprint(api_v1_bp)

    from api.v1.errors import register_error_handlers
    register_error_handlers(app)

    from api.v1.spa import register_spa_routes
    register_spa_routes(app)

    return app


app = create_app()   # 保留模块级 app，兼容 gunicorn `app:app`
```

**为什么不搬旧路由**：`generate_poster_form` 里写着 `url_for("show_poster", poster_id=poster_id)`。Blueprint 会把 endpoint 变成 `legacy.show_poster`，而 `url_for("show_poster")` 在**函数被调用时**才解析。改完代码启动不会报错、跑测试不一定覆盖到、直到用户提交表单才 500。这类回归最难查。

结论：**旧路由留在 `app.py` 原地**，文件变大不是问题，可预测性才是。等 `/api/v1` 稳定后（P2）再考虑拆分，且拆分时必须同步改 `url_for(".show_poster")`。

### 3.2 端口统一（修掉双硬编码）

```python
# config.py（不入库）
PORT = int(os.getenv("PORT", "5000"))

# app.py:383 改为
poster_url = f"{app.config['POSTER_BASE_URL']}/poster/{poster_id}?export=1"

# app.py:407 改为
app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
```

两者读**同一个** `PORT`，从此改端口只需改一处。`POSTER_BASE_URL` 单独保留是因为将来上 HTTPS 反代时，对外域名和内部端口不同。

### 3.3 数据存储

| 项 | 选择 | 理由 |
|---|---|---|
| 数据库 | SQLite（`data/ecard.db`） | 单机、单用户、零运维。数据量级：3000 词 × 若干义项 ≈ 1 万行，SQLite 完全够 |
| ORM | SQLAlchemy 2.0（Declarative + `Mapped[]`） | 类型提示友好，将来换 PostgreSQL 只改 URL |
| 迁移 | Alembic | 词库表结构一定会变（加字段、加义项），手写 `ALTER` 迟早出事 |
| 并发 | `PRAGMA journal_mode=WAL` + `check_same_thread=False` | WAL 允许读写并发，避免导出 PNG 时长事务把写操作卡住 |
| 音频/PDF | 文件系统 `data/audio/`、`data/imports/` | 音频是静态资产，塞 BLOB 进 SQLite 会让备份变重 |

**升级信号**（出现即考虑换 PostgreSQL）：多设备同时写、需要部署到云服务器多实例、单文件超过 1GB。

`data/` 整体在 `.gitignore` 中，**词库种子数据单独放 `data/seed/words.csv` 并在文档中说明来源与许可**，避免"数据不入库"导致换机器无法重建。

### 3.4 请求校验

用 **pydantic v2**（`openai` SDK 已经依赖它，零新增依赖）。

```python
class PracticeCreateIn(BaseModel):
    range: Literal["unit", "theme", "wrongbook", "all"] = "unit"
    range_value: str | None = None
    mode: Literal["zh_to_en", "audio_to_en", "en_to_zh", "phonetic_to_en"] = "zh_to_en"
    size: int = Field(20, ge=5, le=50)
    order: Literal["random", "sequential", "weak_first"] = "random"
    hint_enabled: bool = True
```

校验失败统一转 400 + `VALIDATION_ERROR`，`details` 里逐字段给中文说明。**不再让原始异常字符串出门**。

### 3.5 判题模块（`core/grading.py`）——本方案的技术核心

判题必须**纯函数、无 IO、可单测**。它决定了这个产品"对不对、公不公平"，比任何 UI 都重要。

```python
@dataclass(frozen=True)
class GradeResult:
    correct: bool
    near_miss: bool          # 拼写接近（差 1 个字符且长度≥6）
    distance: int            # 编辑距离
    diff: list[dict]         # 逐字符差异，供前端高亮
    normalized_input: str
    expected: str
```

**规范化顺序（顺序错了结果就错）**：

1. Unicode NFKC（全角字母 → 半角，`ａ` → `a`）
2. 弯引号 `' ' " "` → 直引号
3. 去除首尾空白、连续空白折叠为单空格
4. `lower()`
5. 英文题**不去标点**（`don't` 的撇号是答案的一部分）；中文题去中文标点

**四种题型的判定差异**：

| 题型 | 比较对象 | 特殊规则 |
|---|---|---|
| `zh_to_en` | 词形（`word.form`） | 严格等于；`near_miss` 只提示不判对 |
| `phonetic_to_en` | 词形 | 同上 |
| `audio_to_en` | 词形 | 同上，另记 `replay_count` |
| `en_to_zh` | 义项集合 `sense.meaning_cn` | 命中任一已审核义项即对；去 `的/地/得`；同义写法在 `WordSense.accepted` 里配置 |

**首答正确率单独统计**：`hint_used=true` 的作答计入 `hint_used_count`，**不计入** `first_try_correct`。这是产品公信力的底线——用了提示还算"首答正确"，数据就失去意义。

### 3.6 间隔重复（`core/srs.py`）

MVP 用 **Leitner 盒子**，不用 FSRS/Anki 的完整实现：

| 盒子 | 间隔 | 条件 |
|---|---|---|
| 1 | 1 天 | 答错，或首次进入 |
| 2 | 3 天 | 盒 1 答对 |
| 3 | 7 天 | 盒 2 答对 |
| 4 | 15 天 | 盒 3 答对 |
| 5 | 30 天 | 盒 4 答对 |
| 毕业 | — | 盒 5 答对，移出错词本 |

答错一律回盒 1。`next_review_at = now + interval[box]`。

**为什么不用 FSRS**：需要为每个词维护 stability/difficulty 双参数并做参数拟合，冷启动阶段没有足够作答数据，拟合出来的参数是噪声。Leitner 的规则可以用一句话向家长解释清楚——这在教育产品里是优势不是妥协。留出 `SkillProgress` 表的字段扩展位，将来有数据了再换。

**按技能分离进度**：同一个词，"看中文写英文"对了不等于"听音写词"也对。所以进度主键是 `(learner_id, word_id, skill)`，不是 `(learner_id, word_id)`。

### 3.7 发音服务（`core/audio.py`）

```python
PROVIDER_CHAIN = [LocalCacheProvider, WikimediaProvider, PiperProvider]

def get_audio(word_id, accent="uk") -> AudioResult
    # 1. 查 data/audio/{word_id}/{accent}.mp3，命中直接返回（0 毫秒）
    # 2. 未命中 → 按链尝试 provider
    # 3. 成功则落盘 + 写 manifest（source_url/license/attribution/checksum）
    # 4. 全链失败 → 404 AUDIO_NOT_AVAILABLE，前端显示音标并给出"设备语音"降级按钮
```

**三个必须守住的点**：

1. **商业接口的 key 只在服务端**。金山词霸/有道如果需要接入，key 放 `config.py`，前端永远拿不到。绝不能出现在 Vue bundle 里（打包后会明文躺在 `assets/*.js` 中，任何人 F12 可读）。
2. **不转存商业音频**。商业词典的真人音频是其资产，下载后放进 `data/audio/` 再分发属于侵权。只能用 CC0/CC BY 的 Wikimedia 音频，或本地 TTS 合成。
3. **manifest 必须有 `review_status`**。自动抓来的音频要人工过一遍多音词和专有名词，未审核的不进正式链路。

### 3.8 统一错误契约

**HTTP 状态码表达结果，body 表达原因。不用 `{"code":0}` 这类业务码。**

```json
// 400
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数校验失败",
    "details": [
      {"field": "size", "message": "必须在 5 到 50 之间"}
    ]
  },
  "request_id": "b3f1c2a4"
}
```

理由：`{"code":0}` 方案会让 HTTP 永远是 200，axios 拦截器要二次判断，浏览器 Network 面板看不出成败，CDN/网关的缓存与重试策略也失效。

错误码枚举（全项目统一）：

| code | HTTP | 场景 |
|---|---|---|
| `VALIDATION_ERROR` | 400 | 参数校验失败 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `SESSION_FINISHED` | 409 | 会话已结束仍提交答案 |
| `AUDIO_NOT_AVAILABLE` | 404 | 发音全链失败 |
| `IMPORT_PARSE_FAILED` | 422 | PDF 解析失败 |
| `IMPORT_NOT_REVIEWED` | 409 | 未复核就发布 |
| `AI_UNAVAILABLE` | 503 | DeepSeek 超时/额度不足 |
| `INTERNAL_ERROR` | 500 | 兜底，**不暴露堆栈** |

`request_id` 每次请求生成，同时写日志。用户报错时报这串，能直接定位日志。

### 3.9 日志

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"
)
```

- `before_request` 生成 `request_id` 存入 `g`
- AI 调用、PDF 解析、发音抓取三类**外部依赖**必须记耗时与结果
- 不记录答案内容以外的隐私（demo 阶段无所谓，留好口子）

---

## 4. 前端设计

### 4.1 技术选型

| 层 | 选择 | 理由 |
|---|---|---|
| 框架 | Vue 3（`<script setup>`） | 你其他项目（AiTestHub、教学管理 MVP）都是 Vue3，学习成本为零 |
| 构建 | Vite 5 | 冷启动秒级；`base` 和 `proxy` 配置简单 |
| 状态 | Pinia | 4 个 store 足够：`learner` / `words` / `practice` / `wrongbook` |
| 路由 | Vue Router 4，`createWebHistory('/app/')` | history 模式 URL 干净，靠 Flask 兜底 |
| **UI 库** | **不引入 Element Plus** | 见下 |
| HTTP | axios + 拦截器 | 统一注入 `learner_id`、统一弹错 |

**为什么不引入 Element Plus**：

默写场景的四个核心 UI 元素，Element Plus 一个都不提供现成实现：
1. **大号答题输入框**（字重要够大，移动端要能一屏看完题干和输入框）
2. **逐字符拼写差异高亮**（多打的字母红色删除线、漏打的显示为占位方块）
3. **音标排版**（`/ɪnˈvaɪrənmənt/` 需要专用字体和字距，塞进 `el-input` 会被行高破坏）
4. **音标/听音题的播放按钮 + 播放次数计数**

硬塞进去的结果是到处 `::v-deep` 覆写，反而更重。原型 `prototype/styles.css` 已经把设计 token 定好了，直接迁移成 `styles/tokens.css` + 8 个自建组件，体积和可控性都更好。

### 4.2 路由表

| 路径 | 视图 | 对应原型 |
|---|---|---|
| `/app/` | `DashboardView` | 学习首页 |
| `/app/words` | `WordListView` | 单词库 |
| `/app/practice/setup` | `PracticeSetupView` | 分类默写设置 |
| `/app/practice/run` | `PracticeRunView` | 答题 |
| `/app/practice/result` | `PracticeResultView` | 结果 |
| `/app/wrongbook` | `WrongbookView` | 错词本 |
| `/app/import` | `ImportView` | 词库导入 |
| `/app/settings` | `SettingsView` | 设置 |

### 4.3 SPA 兜底路由（唯一需要小心的地方）

```python
def register_spa_routes(app):
    SPA_DIR = os.path.join(app.root_path, "static", "spa")

    @app.route("/app/", defaults={"path": ""})
    @app.route("/app/<path:path>")
    def spa(path):
        # 绝不能把 /api 吃进来
        if path == "api" or path.startswith("api/"):
            abort(404)
        target = os.path.join(SPA_DIR, path)
        if path and os.path.isfile(target):
            return send_from_directory(SPA_DIR, path)
        return send_from_directory(SPA_DIR, "index.html")   # history fallback
```

三个安全点：
- 前缀锁死 `/app/`，旧路由不受影响
- `send_from_directory` 自带路径穿越防护（`../` 会被拒绝）
- `static/spa/` 不存在时（未构建）返回明确的 503 提示，而不是 500

### 4.4 前端必须预埋的自动化钩子

沿用你既有的约定：**所有可交互元素带 `data-testid`**，供 Playwright 直接定位，不依赖 CSS 类名或动态 id。

```html
<input data-testid="practice-answer-input" />
<button data-testid="practice-submit" />
<button data-testid="practice-next" />
<button data-testid="retry-wrong" />
```

原型里已经这么做了，迁移时**原样保留**，不要改名。

---

## 5. 兼容性红线（7 条，违反任一条即视为回归）

| # | 红线 | 验证方式 |
|---|---|---|
| 1 | `/`、`/poster/<id>`、`/poster-demo/<id>`、`/loading` 返回内容与改造前一致 | 改造前后各截一次图对比 |
| 2 | `POST /api/generate` 返回结构不变（`{"poster_id": "..."}`） | curl 调用比对 |
| 3 | `POST /generate` 仍然 302 到 `/poster/<id>` | 浏览器提交表单 |
| 4 | `GET /api/export/<id>` 仍能下载 PNG | 点导出按钮 |
| 5 | `output/cache/*.json` 的读写路径、文件名规则不变 | 检查 `output/cache/` |
| 6 | `templates/`、`static/css|js`、`services/`、`prompts/` 零改动 | `git diff` 必须为空 |
| 7 | `config.py` 不进 Git | `git ls-files | grep config.py` 必须无输出 |

**建议在 Sprint 1 第一件事就写一个 `tests/test_legacy_contract.py`**，把这 7 条固化成断言。改架构最怕的不是写错，而是不知道写错了。

---

## 6. 风险与对策

| 风险 | 概率 | 影响 | 对策 |
|---|---|---|---|
| 搬旧路由导致 `url_for` 失效 | 中 | 高（表单提交 500） | 第一阶段**不搬**；P2 搬时全局搜索 `url_for(` 逐个改 |
| SPA catch-all 吃掉旧路由 | 中 | 高（旧页面全 404） | 前缀锁 `/app/`；红线 #1 用测试守住 |
| SQLite 写锁导致答题卡顿 | 低 | 中 | WAL 模式；单请求事务尽量短；不在请求里做 PDF 全量解析（改后台线程 + 状态轮询） |
| 音频抓取被限流/许可争议 | 中 | 中 | 三层降级；优先本地 TTS；manifest 记来源；商业音频一律不落盘 |
| PDF 解析准确率不达预期 | 高 | 中 | 定位为"辅助录入"，**强制人工复核**才发布；不在 P0 做 |
| 前端构建产物误入 Git | 中 | 低 | `.gitignore` 已加 `static/spa/`（待补） |
| DeepSeek 调用超时拖垮请求 | 中 | 中 | 显式 timeout；失败返回 503 `AI_UNAVAILABLE`；**判题绝不依赖 AI** |
| 双端口配置漂移 | 中 | 高 | 统一读 `PORT` / `POSTER_BASE_URL`（见 3.2） |

---

## 7. 演进路径

| 阶段 | 内容 | 版本 Tag |
|---|---|---|
| **S0 基线** | 单进程 + 旧功能零改动 + 端口统一 + 契约测试 | `v0.0.1` |
| **S1 骨架** | 应用工厂、`/api/v1` 蓝图、SQLite + Alembic、种子词库、Vite 工程、SPA 兜底路由 | `v0.1.0` |
| **S2 MVP** | 词库查询、练习会话、判题、结果、错词本、发音三层 | `v0.2.0` |
| **S3 增强** | PDF 导入 + 人工复核、全部题型、统计看板 | `v0.3.0` |
| **S4 稳定** | 性能、可访问性、测试覆盖、文档 | `v1.0.0` |

---

## 8. 待确认决策（影响架构落地顺序）

| # | 决策 | 选项 | 我的建议 |
|---|---|---|---|
| A1 | 首版教材版本 | 人教版 / 外研版 / 译林版 | **人教版**（覆盖率最高，且你孩子大概率用这版） |
| A2 | PDF 导入优先级 | P0 / P1 | **P1**（工作量占 MVP 一半以上，先让默写闭环跑通） |
| A3 | MVP 题型 | 4 选 2 / 4 全做 | **`zh_to_en` + `audio_to_en`**，其余进 P2 |
| A4 | 发音首版来源 | Wikimedia / Piper / 商用 | **Piper 本地合成优先**（无网络依赖、无许可风险），Wikimedia 作补充 |
| A5 | 是否做账号 | 无 / 设备 ID / 完整登录 | **无账号，单一默认 learner + localStorage 存 `learner_id`** |
| A6 | 中文判题 | 严格匹配 / 同义词表 | **同义词表**（`WordSense.accepted`），否则"经历/阅历"永远判错 |

---

## 9. 一句话总结

> 这个项目不需要第二个后端，也不需要 CORS。它需要的是：**一个有应用工厂的 Flask、一棵独立在 `/api/v1` 下的契约树、一个挂在 `/app/` 下的 Vue SPA、一份纯函数的判题逻辑，以及一条"旧代码一行不动"的红线。**
