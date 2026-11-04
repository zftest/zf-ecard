# zf-ecard `/api/v1` 接口文档

> 版本：v1.1
> 日期：2026-11-04（v1.1：B3 已实现 7 个接口，并修正三处与数据库不一致的契约）
> 服务基址（开发）：`http://127.0.0.1:5000`
> 服务基址（生产）：同 Flask 端口，SPA 挂在 `/app/`
> 关联文档：`docs/architecture-frontend-backend-separation.md`

---

## 实现状态（2026-11-04，B3 完成）

已实现并通过测试（157 项）：

| 接口 | 状态 |
|---|---|
| `GET /api/v1/health` | ✅ |
| `GET /api/v1/units` | ✅ |
| `GET /api/v1/themes` | ✅ |
| `GET /api/v1/words` | ✅ |
| `GET /api/v1/words/{word_id}` | ✅ |
| `GET /api/v1/learners/{learner_id}` | ✅ |
| `GET /api/v1/learners/{learner_id}/stats/overview` | ✅ |
| `POST /api/v1/practice/sessions` 等（第 7 节起） | ⬜ B4 |

### 三处契约修正（以本文档为准，前端按这里写）

写这份文档时数据库还没建，下面三项与实际实现不一致，现按实现修正 ——
**这一版之后，以下面的写法为准，正文中原有的旧示例以本节为准。**

| 项 | v1.0 写法 | v1.1 实际 | 原因 |
|---|---|---|---|
| `word_id` / `unit_id` / `sense_id` | 字符串 `w_0001` / `u_03` / `s_0001_1` | **整数** | 数据库用自增主键。加前缀需要一层解析，参数格式错时会把 400/404 搅混；而且上下册都有 `U01`，字符串 `u_03` 本身也区分不了册别 |
| `learner_id` | `lrn_default` | **`default`** | 直接等于 `skill_progress.learner_key`，省掉一层映射。拼错（如 `typo`）返回 404，**不会**静默兜底成默认学习者 |
| `skill` 取值 | `zh_to_en` 等 | API 仍收/返**题型名**，数据库存**技能名** | 题型是「这次怎么练」，技能是「练的哪种能力」，将来一个技能可由多个题型练。换算只发生在服务端 `core/vocabulary.py` |

补充两条实现细节：

- `GET /units` 的每一项额外返回 `unit_code`、`unit_no`、`is_starter`、`term`、`book_id`，
  便于前端区分「上册 U01」和「下册 U01」。
- `GET /learners/{id}` 的 `created_at` 取该学习者**最早一次作答时间**；
  从未练习过则为 `null`（MVP 没有 learners 表，不编造"注册时间"）。

---

## 目录

- [0. 阅读指引](#0-阅读指引)
- [1. 通用约定](#1-通用约定)
- [2. 枚举值字典](#2-枚举值字典)
- [3. 数据结构定义](#3-数据结构定义)
- [4. 接口清单总览](#4-接口清单总览)
- [5. 基础与学习者](#5-基础与学习者)
- [6. 词库查询](#6-词库查询)
- [7. 练习与判题](#7-练习与判题)
- [8. 错词本](#8-错词本)
- [9. 发音](#9-发音)
- [10. 词库导入](#10-词库导入)
- [11. 旧接口（冻结，仅供参考）](#11-旧接口冻结仅供参考)
- [12. 错误码总表](#12-错误码总表)

---

## 0. 阅读指引

本文档只描述**新增**的 `/api/v1`。旧的 `/api/generate`、`/api/export/<id>` 属于另一套契约，**保持原样、不再修改**，附录在第 11 节仅供对照。

三个约定先讲清楚，后面不再重复：

1. **所有接口都返回 JSON**（除发音接口返回 `audio/mpeg` 二进制流）。
2. **HTTP 状态码表达结果**，不用 `{"code": 0}` 这种业务码包装。200 就是成功，4xx/5xx 就是失败。
3. **时间一律用 ISO 8601 带时区偏移**，如 `2026-11-03T10:15:00+08:00`。不用时间戳数字，避免前后端时区错位。

---

## 1. 通用约定

### 1.1 请求头

| Header | 必填 | 说明 |
|---|---|---|
| `Content-Type` | POST/PATCH 必填 | `application/json`；上传文件用 `multipart/form-data` |
| `X-Request-Id` | 否 | 前端可自带追踪 ID，未带则服务端生成，响应头回传 |

**MVP 阶段没有鉴权。** 不做登录，靠路径里的 `learner_id` 区分学习者。`learner_id` 由服务端首次启动时 seed 生成，前端存 `localStorage`。这是刻意的取舍——单机自用场景引入登录只会增加摩擦。将来要做多设备同步时，再加 `Authorization: Bearer <token>`，接口结构不用改。

### 1.2 分页约定

列表接口统一用 `page` + `page_size`，返回统一带 `pagination` 对象：

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 137,
    "total_pages": 7
  }
}
```

- `page` 从 **1** 开始（不是 0）
- `page_size` 默认 20，上限 100
- `total_pages` 由服务端算好，前端不自己除

### 1.3 成功响应头

| Header | 说明 |
|---|---|
| `X-Request-Id` | 请求追踪 ID，与错误响应里的 `request_id` 一致 |

### 1.4 统一错误结构

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数校验失败",
    "details": [
      { "field": "size", "message": "必须在 5 到 50 之间" }
    ]
  },
  "request_id": "b3f1c2a4"
}
```

- `code` 是**稳定的机器可读枚举**，前端据此做分支（见第 12 节）
- `message` 是给人看的中文
- `details` 只在 `VALIDATION_ERROR` 时出现
- `request_id` 用于报错排查，日志里能对上

### 1.5 幂等性说明

| 接口 | 幂等 | 说明 |
|---|---|---|
| 所有 `GET` | 是 | 无副作用 |
| `POST /practice/sessions` | 否 | 每次都新建会话 |
| `POST /practice/sessions/{id}/answers` | **否** | 同一题重复提交会**覆盖**该题的作答记录（以最后一次为准），不会重复计数 |
| `POST /imports` | 否 | 每次上传都是新批次 |
| `POST /imports/{id}/publish` | **是** | 已发布的批次再次调用返回 `409 IMPORT_ALREADY_PUBLISHED` |

---

## 2. 枚举值字典

### 2.1 练习题型 `mode`

| 值 | 中文名 | 题干 | 作答 | 判题对象 |
|---|---|---|---|---|
| `zh_to_en` | 汉译英 | 中文释义 | 英文单词 | 词形 |
| `en_to_zh` | 英译汉 | 英文单词 | 中文释义 | 义项集合 |
| `audio_to_en` | 听音写词 | 播放音频（不显示词形） | 英文单词 | 词形 |
| `phonetic_to_en` | 音标写词 | IPA 音标 | 英文单词 | 词形 |

> MVP 只实现 `zh_to_en` 与 `audio_to_en`。另外两个接口已定义好，实现属 P2。

### 2.2 练习范围 `range`

| 值 | 含义 | 需要 `range_value` |
|---|---|---|
| `unit` | 按教材单元 | 是，传 `unit_id` |
| `theme` | 按主题分类 | 是，传主题名 |
| `wrongbook` | 只练错词本 | 否 |
| `all` | 全部词库 | 否 |

### 2.3 出题顺序 `order`

| 值 | 含义 |
|---|---|
| `random` | 随机（默认） |
| `sequential` | 按词库原始顺序 |
| `weak_first` | 薄弱优先（盒子等级低的排前面，同等级随机） |

### 2.4 掌握状态 `status`

| 值 | 含义 | 进入条件 |
|---|---|---|
| `new` | 未学 | 从未作答 |
| `learning` | 学习中 | 盒子 1-3 |
| `reviewing` | 复习中 | 盒子 4-5 |
| `mastered` | 已掌握 | 盒 5 答对毕业 |

### 2.5 技能维度 `skill`

| 值 | 对应题型 | 说明 |
|---|---|---|
| `zh_to_en` | 汉译英 | **进度按技能分开记** |
| `audio_to_en` | 听音写词 | 同一个词，听音写对了不代表看中文也能写对 |
| `en_to_zh` | 英译汉 | |
| `phonetic_to_en` | 音标写词 | |

### 2.6 词性 `pos`

`n.` 名词 / `v.` 动词 / `adj.` 形容词 / `adv.` 副词 / `prep.` 介词 / `conj.` 连词 / `pron.` 代词 / `num.` 数词 / `phr.` 短语

---

## 3. 数据结构定义

### 3.1 `Word`（单词）

```json
{
  "word_id": "w_0001",
  "form": "environment",
  "phonetic_uk": "/ɪnˈvaɪrənmənt/",
  "phonetic_us": "/ɪnˈvaɪrənmənt/",
  "pos": "n.",
  "unit_id": "u_03",
  "unit_name": "Unit 3",
  "theme": "自然与环境",
  "senses": [
    {
      "sense_id": "s_0001_1",
      "meaning_cn": "环境",
      "accepted": ["环境", "自然环境"],
      "example_en": "We should protect the environment.",
      "example_cn": "我们应该保护环境。"
    }
  ],
  "audio": { "uk": true, "us": false },
  "progress": {
    "skill": "zh_to_en",
    "box": 2,
    "status": "learning",
    "correct_count": 5,
    "wrong_count": 2,
    "next_review_at": "2026-11-06T00:00:00+08:00"
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `word_id` | string | 主键，`w_` + 4 位序号 |
| `form` | string | 词形。同一拼写不同词性算**同一个** word，区别在 `senses` |
| `phonetic_uk` / `phonetic_us` | string \| null | 英/美音标，缺失为 `null` |
| `pos` | string | 词性，见 2.6 |
| `unit_id` / `unit_name` | string | 所属教材单元 |
| `theme` | string | 主题分类，如「自然与环境」 |
| `senses` | array | **一个词可以有多个义项**。练习记录绑 `sense_id` 而不是 `word_id`，否则「经历」和「经验」会混成一笔账 |
| `senses[].accepted` | array | 判题时认可的中文写法。**这是中文题判对判错的关键**——没有它，「环境」和「自然环境」这种同义表达永远判错 |
| `audio` | object | 各口音音频是否已就绪，`false` 时前端隐藏播放按钮 |
| `progress` | object \| null | 当前 `learner` 在该 `skill` 下的进度，未学为 `null` |

### 3.2 `Learner`（学习者）

```json
{
  "learner_id": "lrn_default",
  "nickname": "同学",
  "created_at": "2026-11-03T09:00:00+08:00",
  "settings": {
    "daily_goal": 20,
    "default_mode": "zh_to_en",
    "accent": "uk",
    "hint_enabled": true
  }
}
```

### 3.3 `PracticeSession`（练习会话）

```json
{
  "session_id": "ps_9f2c1a7b",
  "learner_id": "lrn_default",
  "mode": "zh_to_en",
  "range": "unit",
  "range_value": "u_03",
  "order": "random",
  "hint_enabled": true,
  "size": 20,
  "status": "running",
  "created_at": "2026-11-03T10:00:00+08:00",
  "expires_at": "2026-11-03T12:00:00+08:00",
  "progress": { "answered": 7, "correct": 5, "wrong": 2 }
}
```

| 字段 | 说明 |
|---|---|
| `status` | `running` / `finished` / `expired` |
| `expires_at` | 会话 2 小时过期，过期后提交答案返回 `409 SESSION_EXPIRED` |

### 3.4 `PracticeItem`（题目）

```json
{
  "item_id": "pi_001",
  "index": 1,
  "word_id": "w_0001",
  "sense_id": "s_0001_1",
  "prompt": "环境",
  "phonetic": null,
  "audio_available": false,
  "hint": "e__________",
  "answered": false
}
```

| 字段 | 按题型的取值 |
|---|---|
| `prompt` | `zh_to_en` → 中文释义；`en_to_zh` → 英文单词；`audio_to_en` → `null`（只给音频）；`phonetic_to_en` → `null` |
| `phonetic` | `phonetic_to_en` → 音标；其他 → `null` |
| `audio_available` | `audio_to_en` → `true`；其他 → `false` |
| `hint` | `hint_enabled=false` 时为 `null`。格式为「首字母 + 下划线占位」，前端只在用户点「提示」时展示 |

> **安全边界说明**：`hint` 随题目一起下发，理论上可在浏览器 devtools 里提前看到。这是有意的取舍——单机自用场景防作弊没有意义，加一个 hint 接口只会让前端多一次请求。作答时前端**如实上报** `hint_used`，统计侧据此把提示后答对排除在首答正确率之外。

### 3.5 `GradeResult`（判题结果）

```json
{
  "item_id": "pi_001",
  "correct": false,
  "near_miss": true,
  "distance": 1,
  "expected": "environment",
  "normalized_input": "enviroment",
  "diff": [
    { "pos": 0, "char": "e", "status": "ok" },
    { "pos": 1, "char": "n", "status": "ok" },
    { "pos": 4, "char": "n", "status": "missing" },
    { "pos": 5, "char": "o", "status": "ok" }
  ],
  "hint_used": true,
  "first_try_correct": false,
  "feedback": "少写了一个 n",
  "answered_at": "2026-11-03T10:03:12+08:00"
}
```

| 字段 | 说明 |
|---|---|
| `correct` | 是否算答对 |
| `near_miss` | **拼写只差 1 个字符且长度 ≥ 6** 时为 `true`。用户看到的提示是「很接近，再检查一下」，但**仍然判错**。这是鼓励而不是放水 |
| `distance` | 编辑距离（Levenshtein） |
| `diff` | 逐字符差异，供前端渲染红色删除线与占位方块 |
| `diff[].status` | `ok` 正确 / `missing` 漏写 / `extra` 多写 / `wrong` 写错 |
| `first_try_correct` | **`correct && !hint_used` 才为 true**。这个词的定义决定统计公信力，不能含糊 |
| `feedback` | 中文提示语，可直接展示 |

---

## 4. 接口清单总览

| # | 接口名 | 方法 | 地址 | 作用 | 阶段 |
|---|---|---|---|---|---|
| 1 | 健康检查 | GET | `/api/v1/health` | 确认服务与数据库可用 | P0 |
| 2 | 获取学习者 | GET | `/api/v1/learners/{learner_id}` | 档案 + 今日概览 | P0 |
| 3 | 统计总览 | GET | `/api/v1/learners/{learner_id}/stats/overview` | 首页数字卡片 | P0 |
| 4 | 单元列表 | GET | `/api/v1/units` | 默写范围选择器 | P0 |
| 5 | 主题列表 | GET | `/api/v1/themes` | 默写范围选择器 | P0 |
| 6 | 单词列表 | GET | `/api/v1/words` | 单词库页，支持搜索筛选分页 | P0 |
| 7 | 单词详情 | GET | `/api/v1/words/{word_id}` | 词条抽屉 | P0 |
| 8 | 创建练习会话 | POST | `/api/v1/practice/sessions` | 按配置抽题 | P0 |
| 9 | 获取练习会话 | GET | `/api/v1/practice/sessions/{session_id}` | 断点续答 | P0 |
| 10 | 提交答案 | POST | `/api/v1/practice/sessions/{session_id}/answers` | 判题 | P0 |
| 11 | 结束练习 | POST | `/api/v1/practice/sessions/{session_id}/finish` | 出报告 + 写错词本 | P0 |
| 12 | 错词本列表 | GET | `/api/v1/learners/{learner_id}/wrongbook` | 待复习清单 | P0 |
| 13 | 更新错词状态 | PATCH | `/api/v1/learners/{learner_id}/wrongbook/{word_id}` | 标记掌握 / 重置 | P1 |
| 14 | 获取发音 | GET | `/api/v1/audio/{word_id}` | 返回 mp3 流 | P0 |
| 15 | 上传词库 | POST | `/api/v1/imports` | 上传 PDF 建批次 | P1 |
| 16 | 查询导入批次 | GET | `/api/v1/imports/{batch_id}` | 轮询解析 + 复核列表 | P1 |
| 17 | 修正导入行 | PATCH | `/api/v1/imports/{batch_id}/items/{item_id}` | 人工复核改错 | P1 |
| 18 | 发布批次 | POST | `/api/v1/imports/{batch_id}/publish` | 落正式词库 | P1 |

---

## 5. 基础与学习者

### 5.1 健康检查

**接口名**：`healthCheck`
**作用**：确认 Flask 进程与 SQLite 可用。给部署探针和前端启动时自检用。
**请求地址**：`GET /api/v1/health`

**请求参数**：无

**请求 demo**

```bash
curl -X GET http://127.0.0.1:5000/api/v1/health
```

**成功返回** `200`

```json
{
  "status": "ok",
  "version": "0.1.0",
  "database": "ok",
  "words_count": 3021,
  "server_time": "2026-11-03T10:00:00+08:00"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `status` | string | 恒为 `ok`，异常时返回 503 |
| `database` | string | `ok` / `degraded`（能连上但表为空） |
| `words_count` | int | 词库条数，用于确认种子数据是否灌入 |

**失败返回** `503`

```json
{
  "error": { "code": "INTERNAL_ERROR", "message": "数据库不可用" },
  "request_id": "a1b2c3d4"
}
```

---

### 5.2 获取学习者

**接口名**：`getLearner`
**作用**：返回学习者档案 + 今日概览（今日目标、已完成、连续天数），驱动首页。
**请求地址**：`GET /api/v1/learners/{learner_id}`

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `learner_id` | string | 是 | 学习者 ID，MVP 固定为 `lrn_default` |

**请求 demo**

```bash
curl -X GET http://127.0.0.1:5000/api/v1/learners/lrn_default
```

```javascript
const res = await axios.get('/api/v1/learners/lrn_default');
```

**成功返回** `200`

```json
{
  "learner_id": "lrn_default",
  "nickname": "同学",
  "created_at": "2026-11-03T09:00:00+08:00",
  "settings": {
    "daily_goal": 20,
    "default_mode": "zh_to_en",
    "accent": "uk",
    "hint_enabled": true
  },
  "today": {
    "date": "2026-11-03",
    "goal": 20,
    "done": 13,
    "accuracy": 0.62,
    "streak_days": 4
  },
  "totals": {
    "learning": 86,
    "reviewing": 41,
    "mastered": 152,
    "wrongbook": 9
  }
}
```

| 字段 | 说明 |
|---|---|
| `today.done` | 今日已作答**题数**（不是去重词数） |
| `today.accuracy` | 今日整体正确率，`null` 表示今日未作答 |
| `totals.learning` | 至少有一个技能处于 `learning` 的词数 |

**失败返回** `404`

```json
{ "error": { "code": "NOT_FOUND", "message": "学习者不存在" }, "request_id": "e5f6a7b8" }
```

---

### 5.3 统计总览

**接口名**：`getStatsOverview`
**作用**：首页四宫格与近 7 日趋势。按技能维度拆分，因为「会写」和「听得懂」是两种能力。
**请求地址**：`GET /api/v1/learners/{learner_id}/stats/overview`

**查询参数**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `days` | int | 否 | 7 | 趋势天数，取值 7 / 14 / 30 |

**请求 demo**

```bash
curl "http://127.0.0.1:5000/api/v1/learners/lrn_default/stats/overview?days=7"
```

**成功返回** `200`

```json
{
  "by_skill": [
    { "skill": "zh_to_en", "learning": 60, "reviewing": 22, "mastered": 90, "accuracy": 0.71 },
    { "skill": "audio_to_en", "learning": 26, "reviewing": 19, "mastered": 62, "accuracy": 0.64 }
  ],
  "trend": [
    { "date": "2026-10-28", "answered": 20, "accuracy": 0.70 },
    { "date": "2026-10-29", "answered": 0,  "accuracy": null },
    { "date": "2026-11-03", "answered": 13, "accuracy": 0.62 }
  ],
  "weak_themes": [
    { "theme": "自然与环境", "accuracy": 0.48, "sampled": 25 },
    { "theme": "校园生活", "accuracy": 0.55, "sampled": 40 }
  ]
}
```

| 字段 | 说明 |
|---|---|
| `trend[].accuracy` | `null` 表示当天没练，前端画图时要断开折线而不是当 0 |
| `weak_themes` | 按正确率升序，只统计 `sampled >= 20` 的主题，避免"练了 1 次全错"排到第一 |

---

## 6. 词库查询

### 6.1 单元列表

**接口名**：`listUnits`
**作用**：默写范围选择器要显示「Unit 3 · 20 词」这样的实时数量，不能前端硬编码。
**请求地址**：`GET /api/v1/units`

**查询参数**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `learner_id` | string | 否 | `lrn_default` | 用于统计每单元的掌握数 |
| `book` | string | 否 | 空 | 教材册次，如「八年级上册」；空表示全部 |

**请求 demo**

```bash
curl "http://127.0.0.1:5000/api/v1/units?learner_id=lrn_default"
```

**成功返回** `200`

```json
{
  "items": [
    {
      "unit_id": "u_01",
      "unit_name": "Unit 1",
      "book": "八年级上册",
      "word_count": 18,
      "mastered_count": 12,
      "wrong_count": 2
    },
    {
      "unit_id": "u_03",
      "unit_name": "Unit 3",
      "book": "八年级上册",
      "word_count": 20,
      "mastered_count": 3,
      "wrong_count": 5
    }
  ]
}
```

> `word_count` 与 `mastered_count` 必须由后端计算。原型阶段曾因为前端写死「20 词」而实际只有 13 条数据，出现「范围胶囊显示 20 词、摘要显示 13 个词」的自相矛盾。

---

### 6.2 主题列表

**接口名**：`listThemes`
**作用**：按主题分类默写的选项来源。
**请求地址**：`GET /api/v1/themes`

**查询参数**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `learner_id` | string | 否 | `lrn_default` | 用于统计 |

**请求 demo**

```bash
curl "http://127.0.0.1:5000/api/v1/themes?learner_id=lrn_default"
```

**成功返回** `200`

```json
{
  "items": [
    { "theme": "自然与环境", "word_count": 28, "mastered_count": 6 },
    { "theme": "校园生活", "word_count": 45, "mastered_count": 20 }
  ]
}
```

---

### 6.3 单词列表

**接口名**：`listWords`
**作用**：单词库页主查询。支持搜索、按单元/主题/词性/状态筛选、排序、分页。
**请求地址**：`GET /api/v1/words`

**查询参数**

| 参数 | 类型 | 必填 | 默认 | 取值/区间 | 注释 |
|---|---|---|---|---|---|
| `learner_id` | string | 否 | `lrn_default` | — | 决定 `progress` 取谁的数据 |
| `q` | string | 否 | 空 | 1-50 字符 | 模糊搜索，同时匹配词形与中文释义；前后空格自动去除 |
| `unit` | string | 否 | 空 | `unit_id` | 如 `u_03` |
| `theme` | string | 否 | 空 | 主题名 | 如 `自然与环境` |
| `pos` | string | 否 | 空 | 见 2.6 | 多值用英文逗号，如 `n.,v.` |
| `status` | string | 否 | 空 | 见 2.4 | 多值用英文逗号，如 `learning,reviewing` |
| `skill` | string | 否 | `zh_to_en` | 见 2.5 | 查哪个技能维度的进度 |
| `sort` | string | 否 | `unit` | `unit` / `alpha` / `wrong_first` / `recent` | `wrong_first` 按错误次数降序 |
| `page` | int | 否 | 1 | ≥ 1 | 页码 |
| `page_size` | int | 否 | 20 | 1-100 | 每页条数 |

**请求 demo**

```bash
curl "http://127.0.0.1:5000/api/v1/words?learner_id=lrn_default&unit=u_03&status=learning&page=1&page_size=20"
```

```javascript
const { data } = await axios.get('/api/v1/words', {
  params: { learner_id: 'lrn_default', q: 'environ', page: 1, page_size: 20 }
});
```

**成功返回** `200`

```json
{
  "items": [
    {
      "word_id": "w_0001",
      "form": "environment",
      "phonetic_uk": "/ɪnˈvaɪrənmənt/",
      "pos": "n.",
      "unit_name": "Unit 3",
      "theme": "自然与环境",
      "meaning_cn": "环境",
      "audio": { "uk": true, "us": false },
      "progress": {
        "skill": "zh_to_en",
        "box": 2,
        "status": "learning",
        "correct_count": 5,
        "wrong_count": 2,
        "next_review_at": "2026-11-06T00:00:00+08:00"
      }
    }
  ],
  "pagination": { "page": 1, "page_size": 20, "total": 18, "total_pages": 1 }
}
```

> 列表接口的 `progress` 可能是 `null`（未学）。前端要能处理，不能直接 `.status` 取值。

**失败返回** `400`

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数校验失败",
    "details": [{ "field": "page_size", "message": "必须在 1 到 100 之间" }]
  },
  "request_id": "c7d8e9f0"
}
```

---

### 6.4 单词详情

**接口名**：`getWord`
**作用**：打开词条抽屉，展示全部义项、例句、发音与逐技能进度。
**请求地址**：`GET /api/v1/words/{word_id}`

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `word_id` | string | 是 | 如 `w_0001` |

**查询参数**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `learner_id` | string | 否 | `lrn_default` | 返回该学习者的进度 |

**请求 demo**

```bash
curl "http://127.0.0.1:5000/api/v1/words/w_0001?learner_id=lrn_default"
```

**成功返回** `200`

返回完整 [`Word`](#31-word单词) 对象，额外带 `progress_by_skill`：

```json
{
  "word_id": "w_0001",
  "form": "environment",
  "phonetic_uk": "/ɪnˈvaɪrənmənt/",
  "phonetic_us": "/ɪnˈvaɪrənmənt/",
  "pos": "n.",
  "unit_id": "u_03",
  "unit_name": "Unit 3",
  "theme": "自然与环境",
  "senses": [
    {
      "sense_id": "s_0001_1",
      "meaning_cn": "环境",
      "accepted": ["环境", "自然环境"],
      "example_en": "We should protect the environment.",
      "example_cn": "我们应该保护环境。"
    }
  ],
  "audio": { "uk": true, "us": false },
  "progress_by_skill": [
    { "skill": "zh_to_en", "box": 2, "status": "learning", "next_review_at": "2026-11-06T00:00:00+08:00" },
    { "skill": "audio_to_en", "box": 1, "status": "learning", "next_review_at": "2026-11-04T00:00:00+08:00" }
  ]
}
```

**失败返回** `404`

```json
{ "error": { "code": "NOT_FOUND", "message": "单词不存在" }, "request_id": "11223344" }
```

---

## 7. 练习与判题

### 7.1 创建练习会话

**接口名**：`createPracticeSession`
**作用**：按「范围 + 题型 + 数量 + 顺序」抽题，返回可直接作答的题目列表。这是整个默写流程的入口。
**请求地址**：`POST /api/v1/practice/sessions`

**请求体**

| 参数 | 类型 | 必填 | 默认 | 取值/区间 | 注释 |
|---|---|---|---|---|---|
| `learner_id` | string | 是 | — | — | 学习者 |
| `range` | string | 是 | — | 见 2.2 | 抽题范围类型 |
| `range_value` | string \| null | 条件必填 | `null` | — | `range=unit` 时传 `unit_id`；`range=theme` 时传主题名 |
| `mode` | string | 是 | — | 见 2.1 | 题型 |
| `size` | int | 否 | 20 | 5-50 | 题目数量。**池子不够时按实际数量返回，并在 `warnings` 里说明** |
| `order` | string | 否 | `random` | 见 2.3 | 出题顺序 |
| `hint_enabled` | bool | 否 | `true` | — | 是否下发首字母提示 |

**请求 demo**

```bash
curl -X POST http://127.0.0.1:5000/api/v1/practice/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "learner_id": "lrn_default",
    "range": "unit",
    "range_value": "u_03",
    "mode": "zh_to_en",
    "size": 20,
    "order": "random",
    "hint_enabled": true
  }'
```

```javascript
const { data } = await axios.post('/api/v1/practice/sessions', {
  learner_id: 'lrn_default',
  range: 'unit',
  range_value: 'u_03',
  mode: 'zh_to_en',
  size: 20,
  order: 'random',
  hint_enabled: true
});
```

**成功返回** `201`

```json
{
  "session_id": "ps_9f2c1a7b",
  "learner_id": "lrn_default",
  "mode": "zh_to_en",
  "range": "unit",
  "range_value": "u_03",
  "order": "random",
  "hint_enabled": true,
  "size": 18,
  "status": "running",
  "created_at": "2026-11-03T10:00:00+08:00",
  "expires_at": "2026-11-03T12:00:00+08:00",
  "items": [
    {
      "item_id": "pi_001",
      "index": 1,
      "word_id": "w_0042",
      "sense_id": "s_0042_1",
      "prompt": "减少",
      "phonetic": null,
      "audio_available": false,
      "hint": "r______",
      "answered": false
    },
    {
      "item_id": "pi_002",
      "index": 2,
      "word_id": "w_0001",
      "sense_id": "s_0001_1",
      "prompt": "环境",
      "phonetic": null,
      "audio_available": false,
      "hint": "e__________",
      "answered": false
    }
  ],
  "warnings": [
    { "code": "POOL_INSUFFICIENT", "message": "该范围只有 18 个词，已按 18 题出题" }
  ]
}
```

| 字段 | 说明 |
|---|---|
| `size` | **返回实际题数**，可能小于请求值 |
| `warnings` | 非致命提示。前端应展示而不是静默忽略 |

**失败返回**

`400` 参数非法：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数校验失败",
    "details": [{ "field": "range_value", "message": "range=unit 时必须提供 range_value" }]
  },
  "request_id": "55667788"
}
```

`409` 词池为空：

```json
{
  "error": { "code": "EMPTY_POOL", "message": "该范围没有可练的词，请先导入词库或更换范围" },
  "request_id": "9900aabb"
}
```

---

### 7.2 获取练习会话

**接口名**：`getPracticeSession`
**作用**：刷新页面或换设备后断点续答；也用于查询当前进度。
**请求地址**：`GET /api/v1/practice/sessions/{session_id}`

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | string | 是 | 创建时返回的 ID |

**查询参数**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `include_answers` | bool | 否 | `false` | 是否带回已作答明细。**只在结果页用，作答中不要开** |

**请求 demo**

```bash
curl "http://127.0.0.1:5000/api/v1/practice/sessions/ps_9f2c1a7b"
```

**成功返回** `200`

```json
{
  "session_id": "ps_9f2c1a7b",
  "learner_id": "lrn_default",
  "mode": "zh_to_en",
  "range": "unit",
  "range_value": "u_03",
  "order": "random",
  "hint_enabled": true,
  "size": 18,
  "status": "running",
  "created_at": "2026-11-03T10:00:00+08:00",
  "expires_at": "2026-11-03T12:00:00+08:00",
  "progress": { "answered": 7, "correct": 5, "wrong": 2 },
  "items": [
    {
      "item_id": "pi_001",
      "index": 1,
      "word_id": "w_0042",
      "prompt": "减少",
      "phonetic": null,
      "audio_available": false,
      "hint": "r______",
      "answered": true
    }
  ]
}
```

**失败返回** `404` / `409 SESSION_EXPIRED`

```json
{ "error": { "code": "SESSION_EXPIRED", "message": "会话已过期，请重新开始练习" }, "request_id": "ccddeeff" }
```

---

### 7.3 提交答案

**接口名**：`submitAnswer`
**作用**：**核心判题接口**。接收一题的作答，返回对错、逐字符差异、提示语，并即时更新该词在对应技能维度上的盒子等级与下次复习时间。
**请求地址**：`POST /api/v1/practice/sessions/{session_id}/answers`

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | string | 是 | 会话 ID |

**请求体**

| 参数 | 类型 | 必填 | 默认 | 取值/区间 | 注释 |
|---|---|---|---|---|---|
| `item_id` | string | 是 | — | — | 题目 ID |
| `answer` | string | 是 | — | 0-100 字符 | 用户原始输入。**不要在前端预处理**（大小写、空格），规范化由服务端统一做 |
| `hint_used` | bool | 否 | `false` | — | 用户是否点过提示。影响 `first_try_correct` |
| `replay_count` | int | 否 | 0 | 0-20 | 听音题音频重播次数 |
| `elapsed_ms` | int | 否 | 0 | 0-600000 | 本题耗时（毫秒） |

**请求 demo**

```bash
curl -X POST http://127.0.0.1:5000/api/v1/practice/sessions/ps_9f2c1a7b/answers \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "pi_001",
    "answer": "enviroment",
    "hint_used": false,
    "replay_count": 0,
    "elapsed_ms": 8200
  }'
```

```javascript
const { data } = await axios.post(
  `/api/v1/practice/sessions/${sessionId}/answers`,
  { item_id, answer, hint_used, replay_count, elapsed_ms }
);
```

**成功返回** `200` —— 注意**答错也是 200**

```json
{
  "item_id": "pi_001",
  "correct": false,
  "near_miss": true,
  "distance": 1,
  "expected": "environment",
  "normalized_input": "enviroment",
  "diff": [
    { "pos": 0, "char": "e", "status": "ok" },
    { "pos": 1, "char": "n", "status": "ok" },
    { "pos": 2, "char": "v", "status": "ok" },
    { "pos": 3, "char": "i", "status": "ok" },
    { "pos": 4, "char": "r", "status": "ok" },
    { "pos": 5, "char": "n", "status": "missing" },
    { "pos": 6, "char": "o", "status": "ok" }
  ],
  "hint_used": false,
  "first_try_correct": false,
  "feedback": "少写了一个 n",
  "progress_updated": {
    "skill": "zh_to_en",
    "box_before": 2,
    "box_after": 1,
    "next_review_at": "2026-11-04T00:00:00+08:00"
  },
  "session_progress": { "answered": 8, "correct": 5, "wrong": 3 },
  "answered_at": "2026-11-03T10:03:12+08:00"
}
```

**答对时的返回**

```json
{
  "item_id": "pi_002",
  "correct": true,
  "near_miss": false,
  "distance": 0,
  "expected": "environment",
  "normalized_input": "environment",
  "diff": [
    { "pos": 0, "char": "e", "status": "ok" }
  ],
  "hint_used": true,
  "first_try_correct": false,
  "feedback": "答对了（用了提示，不计入首答正确率）",
  "progress_updated": {
    "skill": "zh_to_en",
    "box_before": 1,
    "box_after": 2,
    "next_review_at": "2026-11-06T00:00:00+08:00"
  },
  "session_progress": { "answered": 9, "correct": 6, "wrong": 3 },
  "answered_at": "2026-11-03T10:03:40+08:00"
}
```

> **判错是业务结果，不是 HTTP 错误。** 答错返回 200，`correct: false`。只有会话不存在/已结束这类**协议层问题**才返 4xx。这条如果不统一，前端拦截器会把「答错」当成「请求失败」弹全局错误提示。

**失败返回**

`404`

```json
{ "error": { "code": "NOT_FOUND", "message": "题目不存在" }, "request_id": "aabbccdd" }
```

`409` 会话已结束：

```json
{ "error": { "code": "SESSION_FINISHED", "message": "本次练习已结束，请重新开始" }, "request_id": "eeff0011" }
```

---

### 7.4 结束练习

**接口名**：`finishPracticeSession`
**作用**：结束会话，汇总本次成绩，把错词写入错词本，返回结果页所需的全部数据。
**请求地址**：`POST /api/v1/practice/sessions/{session_id}/finish`

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | string | 是 | 会话 ID |

**请求体**：无（可为空对象）

**请求 demo**

```bash
curl -X POST http://127.0.0.1:5000/api/v1/practice/sessions/ps_9f2c1a7b/finish \
  -H "Content-Type: application/json" -d '{}'
```

**成功返回** `200`

```json
{
  "session_id": "ps_9f2c1a7b",
  "mode": "zh_to_en",
  "status": "finished",
  "size": 20,
  "answered": 20,
  "correct": 11,
  "wrong": 9,
  "accuracy": 0.55,
  "first_try_correct": 8,
  "first_try_accuracy": 0.4,
  "hint_used_count": 3,
  "duration_ms": 384000,
  "avg_elapsed_ms": 19200,
  "wrong_items": [
    {
      "item_id": "pi_001",
      "word_id": "w_0001",
      "form": "environment",
      "meaning_cn": "环境",
      "user_answer": "enviroment",
      "expected": "environment",
      "near_miss": true,
      "next_review_at": "2026-11-04T00:00:00+08:00"
    }
  ],
  "wrongbook_added": 9,
  "next_review_at": "2026-11-04T00:00:00+08:00",
  "suggestions": [
    "错词集中在 Unit 3 的名词，共 6 个",
    "明天先复习这 9 个错词，预计 5 分钟"
  ]
}
```

| 字段 | 说明 |
|---|---|
| `answered` | 实际作答题数，可能小于 `size`（中途退出） |
| `first_try_accuracy` | `first_try_correct / answered`。**这是产品公信力的核心指标**，不能用 `accuracy` 替代 |
| `wrong_items` | 只列错题，供「只练本次错词」按钮构造新会话 |
| `suggestions` | 规则生成的中文建议，非 AI 生成（AI 生成会不稳定且慢） |

**幂等性**：重复调用返回同样结果，不会重复写错词本。

**失败返回** `404` / `409 SESSION_EXPIRED`

---

## 8. 错词本

### 8.1 错词本列表

**接口名**：`listWrongbook`
**作用**：错词本页。默认按「到期优先」排序，让用户先复习该复习的。
**请求地址**：`GET /api/v1/learners/{learner_id}/wrongbook`

**查询参数**

| 参数 | 类型 | 必填 | 默认 | 取值/区间 | 注释 |
|---|---|---|---|---|---|
| `due_before` | string | 否 | 空 | ISO 8601 | 只返回该时间点前到期的词；不传返回全部 |
| `skill` | string | 否 | 空 | 见 2.5 | 筛选技能维度 |
| `sort` | string | 否 | `due` | `due` / `wrong_count` / `recent` | `due` 按到期时间升序 |
| `page` | int | 否 | 1 | ≥ 1 | |
| `page_size` | int | 否 | 20 | 1-100 | |

**请求 demo**

```bash
curl "http://127.0.0.1:5000/api/v1/learners/lrn_default/wrongbook?due_before=2026-11-03T23:59:59%2B08:00&sort=due"
```

**成功返回** `200`

```json
{
  "items": [
    {
      "word_id": "w_0001",
      "form": "environment",
      "phonetic_uk": "/ɪnˈvaɪrənmənt/",
      "meaning_cn": "环境",
      "pos": "n.",
      "unit_name": "Unit 3",
      "skill": "zh_to_en",
      "box": 1,
      "wrong_count": 3,
      "status": "learning",
      "next_review_at": "2026-11-03T00:00:00+08:00",
      "is_due": true,
      "last_wrong_at": "2026-11-02T19:20:00+08:00"
    }
  ],
  "pagination": { "page": 1, "page_size": 20, "total": 9, "total_pages": 1 },
  "summary": { "total": 9, "due_today": 6, "mastered_this_week": 4 }
}
```

| 字段 | 说明 |
|---|---|
| `is_due` | 是否已到复习时间。前端据此决定是否给「现在复习」高亮 |
| `summary.due_today` | 今日待复习数，用于侧边栏角标 |

---

### 8.2 更新错词状态

**接口名**：`updateWrongbookEntry`
**作用**：手动标记「已掌握」（移出错词本），或把状态重置回盒子 1。用于用户自己判断「这个词我其实会」的场景。
**请求地址**：`PATCH /api/v1/learners/{learner_id}/wrongbook/{word_id}`

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `learner_id` | string | 是 | 学习者 |
| `word_id` | string | 是 | 单词 |

**请求体**

| 参数 | 类型 | 必填 | 取值 | 注释 |
|---|---|---|---|---|
| `skill` | string | 是 | 见 2.5 | 只改这个技能维度的状态 |
| `action` | string | 是 | `master` / `reset` | `master` 移到已掌握；`reset` 回盒子 1 |

**请求 demo**

```bash
curl -X PATCH http://127.0.0.1:5000/api/v1/learners/lrn_default/wrongbook/w_0001 \
  -H "Content-Type: application/json" \
  -d '{ "skill": "zh_to_en", "action": "master" }'
```

**成功返回** `200`

```json
{
  "word_id": "w_0001",
  "skill": "zh_to_en",
  "status": "mastered",
  "box": 5,
  "next_review_at": null,
  "updated_at": "2026-11-03T10:20:00+08:00"
}
```

**失败返回** `404`

```json
{ "error": { "code": "NOT_FOUND", "message": "该词不在此技能维度的错词本中" }, "request_id": "22334455" }
```

---

## 9. 发音

### 9.1 获取发音

**接口名**：`getWordAudio`
**作用**：返回单词指定口音的 mp3 二进制流。按「本地缓存 → Wikimedia CC0/CC BY → Piper 本地合成」三层降级，全失败返回 404。
**请求地址**：`GET /api/v1/audio/{word_id}`

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `word_id` | string | 是 | 单词 ID |

**查询参数**

| 参数 | 类型 | 必填 | 默认 | 取值 | 注释 |
|---|---|---|---|---|---|
| `accent` | string | 否 | `uk` | `uk` / `us` | 英式/美式 |

**请求 demo**

```bash
curl -X GET "http://127.0.0.1:5000/api/v1/audio/w_0001?accent=uk" --output word.mp3
```

```javascript
// 直接绑给 <audio> 的 src，浏览器自带缓存
const src = `/api/v1/audio/${wordId}?accent=uk`;
```

**成功返回** `200`

- `Content-Type: audio/mpeg`
- `Content-Length`: 文件字节数
- `Cache-Control: public, max-age=31536000, immutable`
- `X-Audio-Source`: `cache` / `wikimedia` / `piper`（用于排查来源）

**失败返回** `404`

```json
{ "error": { "code": "AUDIO_NOT_AVAILABLE", "message": "该词暂无发音，可改用设备语音" }, "request_id": "33445566" }
```

**前端降级要求**：收到 404 后，**不要**弹全局错误。应展示音标文本，并把播放按钮切到「设备语音（演示）」态，用 `SpeechSynthesis` 兜底，且**明确标注这不是真人发音**——原型里已经这么做，迁移时保留。

**为什么用 302/流而不是返回 URL**：
- 返回流可以用 `Cache-Control: immutable` 让浏览器永久缓存，第二次播放零请求
- 音频来源可能随时从 Pipler 切到 Wikimedia，URL 会变；接口地址不变
- 不暴露文件系统的真实路径

---

## 10. 词库导入

> 这一组接口属 **P1**，MVP 不做。设计先定死，是为了让前端页面结构能提前搭好。

### 10.1 上传词库

**接口名**：`createImportBatch`
**作用**：上传 PDF（或 CSV/JSON），创建解析批次，立即返回批次 ID，解析在后台进行。
**请求地址**：`POST /api/v1/imports`

**请求头**：`Content-Type: multipart/form-data`

**表单字段**

| 字段 | 类型 | 必填 | 取值/区间 | 注释 |
|---|---|---|---|---|
| `file` | file | 是 | ≤ 20MB | 支持 `.pdf` / `.csv` / `.json` |
| `book` | string | 否 | — | 教材册次，如「八年级上册」 |
| `unit_name` | string | 否 | — | 整份文件归属的单元；PDF 内若已标注单元则留空 |
| `auto_merge` | bool | 否 | 默认 `true` | 是否让 AI 协助合并被拆散的词条字段 |

**请求 demo**

```bash
curl -X POST http://127.0.0.1:5000/api/v1/imports \
  -F "file=@初中词汇表.pdf" \
  -F "book=八年级上册" \
  -F "auto_merge=true"
```

```javascript
const form = new FormData();
form.append('file', fileInput.files[0]);
form.append('book', '八年级上册');
const { data } = await axios.post('/api/v1/imports', form, {
  headers: { 'Content-Type': 'multipart/form-data' }
});
```

**成功返回** `202`

```json
{
  "batch_id": "ib_4d5e6f7a",
  "filename": "初中词汇表.pdf",
  "status": "parsing",
  "created_at": "2026-11-03T10:30:00+08:00",
  "estimated_seconds": 15
}
```

| `status` | 含义 |
|---|---|
| `parsing` | 解析中，前端每 2 秒轮询 |
| `reviewing` | 解析完成，待人工复核 |
| `published` | 已发布进正式词库 |
| `failed` | 解析失败，看 `error_message` |

**失败返回**

`400` 类型不支持：

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "仅支持 pdf/csv/json" }, "request_id": "44556677" }
```

`413` 文件过大：

```json
{ "error": { "code": "FILE_TOO_LARGE", "message": "文件超过 20MB 上限" }, "request_id": "55667788" }
```

---

### 10.2 查询导入批次

**接口名**：`getImportBatch`
**作用**：轮询解析进度；解析完成后返回逐行复核数据与冲突项。
**请求地址**：`GET /api/v1/imports/{batch_id}`

**查询参数**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `page` | int | 否 | 1 | 复核行分页 |
| `page_size` | int | 否 | 50 | 上限 200 |
| `only_conflict` | bool | 否 | `false` | 只看有冲突的行 |

**请求 demo**

```bash
curl "http://127.0.0.1:5000/api/v1/imports/ib_4d5e6f7a?page=1&page_size=50"
```

**成功返回** `200`

```json
{
  "batch_id": "ib_4d5e6f7a",
  "filename": "初中词汇表.pdf",
  "status": "reviewing",
  "created_at": "2026-11-03T10:30:00+08:00",
  "summary": {
    "total_rows": 120,
    "parsed_ok": 112,
    "needs_review": 8,
    "conflicts": 3
  },
  "items": [
    {
      "item_id": "ii_001",
      "row_no": 1,
      "form": "environment",
      "phonetic": "/ɪnˈvaɪrənmənt/",
      "pos": "n.",
      "meaning_cn": "环境",
      "unit_name": "Unit 3",
      "confidence": 0.98,
      "status": "ok",
      "conflicts": []
    },
    {
      "item_id": "ii_045",
      "row_no": 45,
      "form": "pre sent",
      "phonetic": null,
      "pos": null,
      "meaning_cn": "礼物；现在",
      "unit_name": "Unit 5",
      "confidence": 0.41,
      "status": "needs_review",
      "conflicts": [
        { "field": "form", "type": "SPLIT_WORD", "message": "疑似被 PDF 分栏拆开，建议合并为 present" },
        { "field": "meaning_cn", "type": "MULTI_SENSE", "message": "一个词对应两个义项，建议拆成两条" }
      ]
    }
  ],
  "pagination": { "page": 1, "page_size": 50, "total": 120, "total_pages": 3 }
}
```

| 字段 | 说明 |
|---|---|
| `confidence` | 0-1。**< 0.75 一律进 `needs_review`**，不允许自动发布 |
| `status` | `ok` / `needs_review` / `fixed` / `skipped` |
| `conflicts[].type` | `SPLIT_WORD` 分栏拆词 / `MULTI_SENSE` 多义项 / `DUPLICATE` 与现有词库重复 / `MISSING_FIELD` 字段缺失 |

---

### 10.3 修正导入行

**接口名**：`updateImportItem`
**作用**：人工复核时修正单行。这是「AI 只提建议、人做决定」原则的落地。
**请求地址**：`PATCH /api/v1/imports/{batch_id}/items/{item_id}`

**请求体**（按需传，只传要改的字段）

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `form` | string | 否 | 词形 |
| `phonetic` | string \| null | 否 | 音标 |
| `pos` | string \| null | 否 | 词性 |
| `meaning_cn` | string | 否 | 中文释义 |
| `unit_name` | string | 否 | 单元 |
| `status` | string | 否 | `ok` / `fixed` / `skipped` |

**请求 demo**

```bash
curl -X PATCH http://127.0.0.1:5000/api/v1/imports/ib_4d5e6f7a/items/ii_045 \
  -H "Content-Type: application/json" \
  -d '{ "form": "present", "meaning_cn": "礼物", "status": "fixed" }'
```

**成功返回** `200`

```json
{
  "item_id": "ii_045",
  "form": "present",
  "status": "fixed",
  "updated_at": "2026-11-03T10:35:00+08:00",
  "batch_summary": { "total_rows": 120, "needs_review": 7, "conflicts": 2 }
}
```

---

### 10.4 发布批次

**接口名**：`publishImportBatch`
**作用**：把复核通过的批次写入正式词库。
**请求地址**：`POST /api/v1/imports/{batch_id}/publish`

**请求体**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `skip_unreviewed` | bool | 否 | `false` | `true` 时跳过未复核行；`false` 时有未复核行则拒绝发布 |

**请求 demo**

```bash
curl -X POST http://127.0.0.1:5000/api/v1/imports/ib_4d5e6f7a/publish \
  -H "Content-Type: application/json" -d '{ "skip_unreviewed": false }'
```

**成功返回** `200`

```json
{
  "batch_id": "ib_4d5e6f7a",
  "status": "published",
  "published_at": "2026-11-03T10:40:00+08:00",
  "words_created": 118,
  "words_updated": 2,
  "words_skipped": 0
}
```

**失败返回** `409`

```json
{
  "error": {
    "code": "IMPORT_NOT_REVIEWED",
    "message": "还有 7 行未复核，请处理后再发布",
    "details": [{ "field": "needs_review", "message": "7 行" }]
  },
  "request_id": "66778899"
}
```

---

## 11. 旧接口（冻结，仅供参考）

以下接口**不在本次改造范围内，保持不变**。列出仅为避免与 `/api/v1` 混淆。

| 接口名 | 方法 | 地址 | 返回 | 状态 |
|---|---|---|---|---|
| 生成知识卡 | POST | `/api/generate` | `{"poster_id": "abc123def456"}` | 冻结 |
| 表单生成并跳转 | POST | `/generate` | `302 → /poster/<id>` | 冻结 |
| 导出 PNG | GET | `/api/export/<poster_id>` | `image/png` 附件 | 冻结 |

**冻结的含义**：不改路径、不改返回结构、不改错误格式。哪怕它返回的是 `{"error": "..."}` 这种和 `/api/v1` 不一致的形态，也不动——改它会同时改动 `templates/` 与 `static/js/main.js`，收益为零、回归风险为正。

---

## 12. 错误码总表

| code | HTTP | 触发场景 | 前端建议处理 |
|---|---|---|---|
| `VALIDATION_ERROR` | 400 | 参数缺失/类型错/越界 | 逐字段标红，展示 `details[].message` |
| `FILE_TOO_LARGE` | 413 | 上传超 20MB | 提示压缩或拆分 |
| `NOT_FOUND` | 404 | 单词/会话/批次不存在 | 提示并返回列表页 |
| `SESSION_FINISHED` | 409 | 会话已结束仍提交 | 自动跳结果页 |
| `SESSION_EXPIRED` | 409 | 会话超 2 小时 | 提示重新开始 |
| `EMPTY_POOL` | 409 | 抽题范围为空 | 引导换范围或导入词库 |
| `IMPORT_NOT_REVIEWED` | 409 | 有未复核行就发布 | 定位到第一个冲突行 |
| `IMPORT_ALREADY_PUBLISHED` | 409 | 重复发布 | 忽略，刷新状态即可 |
| `IMPORT_PARSE_FAILED` | 422 | PDF 解析失败 | 展示 `error_message`，建议改 CSV |
| `AUDIO_NOT_AVAILABLE` | 404 | 三层发音全失败 | **不弹全局错**，切设备语音并标注 |
| `AI_UNAVAILABLE` | 503 | DeepSeek 超时/额度不足 | 提示稍后重试，**降级为不影响判题** |
| `INTERNAL_ERROR` | 500 | 未捕获异常 | 展示 `request_id` 让用户反馈 |

**一条纪律**：任何 500 都**不得**把 Python 异常字符串返回给前端。只返回固定文案 + `request_id`，堆栈进日志。现有 `app.py:303` 的 `f"AI 生成失败：{str(e)}"` 就是反面例子。

---

## 附：与前端 store 的对应关系

| Store | 使用的接口 |
|---|---|
| `stores/learner.js` | `getLearner`、`getStatsOverview` |
| `stores/words.js` | `listUnits`、`listThemes`、`listWords`、`getWord` |
| `stores/practice.js` | `createPracticeSession`、`getPracticeSession`、`submitAnswer`、`finishPracticeSession` |
| `stores/wrongbook.js` | `listWrongbook`、`updateWrongbookEntry` |

`getWordAudio` 不进 store，直接拼 URL 给 `<audio src>`，让浏览器 HTTP 缓存生效。
