# 知识卡生成系统接口文档（现状版）

| 文档项 | 内容 |
|---|---|
| 文档版本 | v1.0 |
| 适用项目 | `knowledge-card-generato-main` |
| 整理日期 | 2026-11-02 |
| 代码依据 | `app.py`、`services/deepseek_client.py`、`services/poster_exporter.py`、现有模板与 JS |
| 本地 Base URL | `http://127.0.0.1:5000` |
| 接口风格 | Flask 路由；JSON API + 表单提交 + 服务端 HTML 页面 |
| 鉴权 | 当前无鉴权，仅建议在本地或受信环境使用 |

> 本文档描述“当前已经实现的接口”，不包含初中单词与分类默写的规划接口。新功能接口草案见产品规格说明书。

## 1. 项目架构与前后端分离结论

### 1.1 当前架构

```text
浏览器
  ├─ Jinja2 模板：index / poster / poster-demo / loading
  ├─ 原生 JavaScript：表单校验、Loading、跨标签页通知
  └─ HTML 表单 / 下载链接
          │
          ▼
Flask app.py
  ├─ 页面路由：返回 HTML
  ├─ 表单路由：POST /generate，成功后 302 跳转
  ├─ JSON 路由：POST /api/generate
  ├─ 文件路由：GET /api/export/<poster_id>
  └─ services：DeepSeek 内容生成、Playwright 海报截图
          │
          ▼
文件缓存 output/cache/<poster_id>.json
图片输出 output/poster_<poster_id>.png
```

### 1.2 是否支持前后端分离

**结论：当前属于“半分离”，具备 API 化基础，但还不是完整的前后端分离项目。**

| 判断项 | 当前状态 | 说明 |
|---|---|---|
| 独立前端工程 | 不支持 | 没有 Vue/React 等独立前端工程，HTML 位于 Flask `templates/` |
| 服务端模板依赖 | 强依赖 | 页面使用 Jinja2 的 `url_for`、模板变量与 `render_template` |
| JSON 数据接口 | 部分支持 | 已有 `/api/generate`，可用于独立前端生成知识卡 |
| 文件下载接口 | 支持 | 已有 `/api/export/<poster_id>`，返回 PNG 二进制 |
| 同源调用 | 支持 | 当前页面与 API 同域，无需跨域配置 |
| 跨域调用 | 未配置 | 前端若运行在 `localhost:5173` 等不同源，需要增加 CORS 策略 |
| API 版本管理 | 未支持 | 当前没有 `/api/v1` 版本前缀 |
| 统一响应结构 | 未支持 | 成功仅返回 `poster_id`，失败仅返回 `error` |
| OpenAPI/Swagger | 未提供 | 本文档是依据代码整理，不是自动生成的在线文档 |
| 鉴权与权限 | 未提供 | 当前接口公开可调用 |
| 异步任务查询 | 未提供 | 生成请求同步等待 DeepSeek 返回，没有任务 ID 与进度查询接口 |

### 1.3 推荐演进方式

不建议为了“前后端分离”推倒重写。推荐 **API 优先、渐进分离**：

1. 保留现有知识卡页面与接口，避免回归。
2. 新功能使用 `/api/v1/...`，按资源拆分 Flask Blueprint。
3. 统一新接口的请求校验、错误码和响应结构。
4. 默写模块可先用响应式 Web 页面验证产品；需要复杂交互或独立部署时再迁移到 Vue3。
5. 前后端不同端口开发时，再按开发/生产环境配置 CORS，而不是默认完全放开。

## 2. 通用约定

### 2.1 内容类型

| 场景 | Content-Type |
|---|---|
| JSON 请求 | `application/json; charset=utf-8` |
| JSON 响应 | `application/json` |
| 表单请求 | `application/x-www-form-urlencoded` 或浏览器表单默认格式 |
| 页面响应 | `text/html; charset=utf-8` |
| PNG 下载 | `image/png` |

### 2.2 通用变量定义

| 变量 | 位置 | 类型 | 必填 | 默认值 | 定义与约束 |
|---|---|---|---|---|---|
| `grade` | JSON / Form | string | 是 | 无 | 年级，如“三年级”“七年级”；当前后端未做枚举白名单校验 |
| `subject` | JSON / Form | string | 是 | 无 | 学科；业务支持“数学”“英语”“语文”，未知学科会在提示词加载时失败 |
| `book` | JSON / Form | string | 是 | 无 | 册别，如“上册”“下册” |
| `publisher` | JSON / Form | string | 是 | 无 | 教材版本/出版社，如“人教版”“外研版”“译林版” |
| `unit_name` | JSON / Form | string | 是 | 无 | 单元名称或主题，如“第一单元”“分数加法” |
| `stage` | JSON / Form | string | 否 | `小学` | 学段；页面提供“小学”“初中”“高中”，其他值会按默认考试关键词处理 |
| `poster_id` | Path | string | 是 | 无 | 海报唯一标识；生成时取 UUID4 十六进制字符串前 12 位 |
| `demo` | Query | string | 否 | `0` | `/poster/<poster_id>` 的版式开关；值为 `1` 时使用新版 `poster-demo.html` |

> 注意：后端目前只通过真值判断检查必填字段，没有完整的长度、类型、枚举、空白字符串校验。调用方仍应传合法字符串。

### 2.3 当前响应风格

当前没有统一响应包装，按接口分别返回：

- 生成成功：`{"poster_id": "..."}`
- 业务失败：`{"error": "..."}`
- PNG 成功：直接返回文件流
- 表单失败：纯文本
- 页面不存在或缓存缺失：纯文本/HTML

## 3. 接口总览

| 分类 | 接口名 | 方法 | 地址 | 成功响应 |
|---|---|---|---|---|
| 数据 API | 生成知识卡 | POST | `/api/generate` | JSON：`poster_id` |
| 数据 API | 导出知识卡 PNG | GET | `/api/export/{poster_id}` | PNG 文件 |
| 表单接口 | 表单生成并跳转海报 | POST | `/generate` | 302 重定向 |
| 页面路由 | 首页 | GET | `/` | HTML |
| 页面路由 | 海报预览 | GET | `/poster/{poster_id}` | HTML |
| 页面路由 | 新版海报预览 | GET | `/poster-demo/{poster_id}` | HTML |
| 页面路由 | 加载等待页 | GET | `/loading` | HTML |

## 4. 数据 API

### 4.1 生成知识卡

| 项目 | 内容 |
|---|---|
| 接口名 | 生成知识卡 |
| 接口地址 | `/api/generate` |
| 请求方法 | `POST` |
| 功能说明 | 接收年级、学科、教材和单元信息，同步调用 DeepSeek 生成知识卡，写入文件缓存并返回海报 ID |
| 请求格式 | JSON |
| 鉴权 | 无 |
| 幂等性 | 否；每次成功请求都会生成新的 `poster_id` |
| 预计耗时 | 页面提示约 15～30 秒，实际取决于模型与网络 |

#### 请求参数

| 参数 | 类型 | 必填 | 示例 | 说明 |
|---|---|---|---|---|
| `grade` | string | 是 | `七年级` | 年级 |
| `subject` | string | 是 | `英语` | 学科 |
| `book` | string | 是 | `上册` | 册别 |
| `publisher` | string | 是 | `人教版` | 教材版本 |
| `unit_name` | string | 是 | `Unit 1` | 单元名称 |
| `stage` | string | 否 | `初中` | 学段；省略时为 `小学` |

#### 请求 Demo

```bash
curl -X POST "http://127.0.0.1:5000/api/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "grade": "七年级",
    "subject": "英语",
    "book": "上册",
    "publisher": "人教版",
    "unit_name": "Unit 1",
    "stage": "初中"
  }'
```

JavaScript Demo：

```javascript
const response = await fetch("http://127.0.0.1:5000/api/generate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    grade: "七年级",
    subject: "英语",
    book: "上册",
    publisher: "人教版",
    unit_name: "Unit 1",
    stage: "初中"
  })
});

const result = await response.json();
if (!response.ok) throw new Error(result.error || "生成失败");
console.log(result.poster_id);
```

#### 成功返回

HTTP `200 OK`

```json
{
  "poster_id": "a1b2c3d4e5f6"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `poster_id` | string | 海报 ID；用于访问预览页和调用 PNG 导出接口 |

成功后可访问：

```text
GET /poster/a1b2c3d4e5f6
GET /poster-demo/a1b2c3d4e5f6
GET /api/export/a1b2c3d4e5f6
```

#### 失败返回

参数不完整，HTTP `400 Bad Request`：

```json
{
  "error": "请填写完整信息"
}
```

DeepSeek 调用、提示词加载或 JSON 解析失败，HTTP `500 Internal Server Error`：

```json
{
  "error": "AI 生成失败：具体异常信息"
}
```

#### 实现注意事项

- 该接口是同步请求，调用方需要设置合理超时并防止重复点击。
- 生成结果保存到 `output/cache/<poster_id>.json`，服务重启后文件仍存在。
- 当前 `500` 响应会直接拼接异常文本，可能暴露内部实现细节；生产环境应改为通用错误信息并记录服务端日志。
- 非法 JSON 可能进入 Flask 默认错误处理，不保证仍使用上述 JSON 错误结构。

### 4.2 导出知识卡 PNG

| 项目 | 内容 |
|---|---|
| 接口名 | 导出知识卡 PNG |
| 接口地址 | `/api/export/{poster_id}` |
| 请求方法 | `GET` |
| 功能说明 | 根据海报 ID 读取缓存，使用 Playwright 访问海报页并截图，返回 PNG 附件 |
| 请求参数 | 仅路径参数，无请求体 |
| 鉴权 | 无 |

#### 路径参数

| 参数 | 类型 | 必填 | 示例 | 说明 |
|---|---|---|---|---|
| `poster_id` | string | 是 | `a1b2c3d4e5f6` | 生成知识卡接口返回的海报 ID |

#### 请求 Demo

```bash
curl -X GET "http://127.0.0.1:5000/api/export/a1b2c3d4e5f6" \
  -o "知识卡_a1b2c3d4e5f6.png"
```

浏览器也可以直接访问：

```html
<a href="/api/export/a1b2c3d4e5f6">下载知识卡 PNG</a>
```

#### 成功返回

HTTP `200 OK`

| 响应项 | 内容 |
|---|---|
| `Content-Type` | `image/png` |
| `Content-Disposition` | 附件下载 |
| 下载文件名 | `知识卡_<poster_id>.png` |
| 响应体 | PNG 二进制文件流 |

#### 失败返回

海报缓存不存在，HTTP `404 Not Found`：

```json
{
  "error": "海报数据不存在，请重新生成"
}
```

截图或文件处理失败，HTTP `500 Internal Server Error`：

```json
{
  "error": "截图失败：具体异常信息"
}
```

#### 实现注意事项

- 导出逻辑内部访问 `http://127.0.0.1:5000/poster/<poster_id>?export=1`，端口当前为硬编码。
- 若修改 Flask 监听端口，必须同步调整导出 URL，否则导出会失败。
- 导出是同步操作，且会启动 Chromium；高并发场景需要任务队列、资源限制和超时治理。
- 当前没有缓存清理接口或 TTL 机制；缓存文件存在才能导出。

## 5. 表单接口

### 5.1 表单生成并跳转海报

| 项目 | 内容 |
|---|---|
| 接口名 | 表单生成知识卡 |
| 接口地址 | `/generate` |
| 请求方法 | `POST` |
| 请求格式 | 表单字段 |
| 功能说明 | 与 JSON 生成接口使用相同业务逻辑；成功后直接 302 跳转到海报预览页 |
| 当前用途 | 首页 `<form action="/generate" target="_blank">` 新标签页打开海报 |

#### 请求参数

使用第 2.2 节的 `grade`、`subject`、`book`、`publisher`、`unit_name`、`stage`，含义一致。

#### 请求 Demo

```html
<form method="POST" action="/generate" target="_blank">
  <input name="grade" value="七年级" />
  <input name="subject" value="英语" />
  <input name="book" value="上册" />
  <input name="publisher" value="人教版" />
  <input name="unit_name" value="Unit 1" />
  <input name="stage" value="初中" />
  <button type="submit">生成知识卡</button>
</form>
```

#### 成功返回

HTTP `302 Found`

```text
Location: /poster/a1b2c3d4e5f6
```

#### 失败返回

| 状态码 | 响应格式 | 示例 |
|---|---|---|
| `400` | 纯文本 | `请填写完整信息` |
| `500` | 纯文本 | `AI 生成失败：具体异常信息` |

> 此接口是浏览器表单工作流，不建议独立 SPA 使用；SPA 应使用 `/api/generate`。

## 6. 页面路由

这些地址返回 HTML，不属于 JSON API，但属于当前系统完整的对外路由清单。

### 6.1 首页

| 项目 | 内容 |
|---|---|
| 接口名 | 知识卡生成首页 |
| 方法/地址 | `GET /` |
| 请求参数 | 无 |
| 返回结果 | `index.html` |
| Demo | `http://127.0.0.1:5000/` |

### 6.2 海报预览

| 项目 | 内容 |
|---|---|
| 接口名 | 海报预览页 |
| 方法/地址 | `GET /poster/{poster_id}` |
| 路径参数 | `poster_id`：海报 ID |
| Query 参数 | `demo`：可选；`1` 使用新版模板，其他值使用默认模板 |
| 成功返回 | `poster.html` 或 `poster-demo.html` |
| 失败返回 | HTTP `404`，纯文本 `海报已过期，请重新生成` |
| Demo | `http://127.0.0.1:5000/poster/a1b2c3d4e5f6` |

新版版式 Demo：

```text
http://127.0.0.1:5000/poster/a1b2c3d4e5f6?demo=1
```

### 6.3 新版海报预览

| 项目 | 内容 |
|---|---|
| 接口名 | 新版左右分栏海报页 |
| 方法/地址 | `GET /poster-demo/{poster_id}` |
| 路径参数 | `poster_id`：海报 ID |
| 成功返回 | `poster-demo.html` |
| 失败返回 | HTTP `404`，纯文本 `海报已过期，请重新生成` |
| Demo | `http://127.0.0.1:5000/poster-demo/a1b2c3d4e5f6` |

### 6.4 加载等待页

| 项目 | 内容 |
|---|---|
| 接口名 | 生成等待页 |
| 方法/地址 | `GET /loading` |
| 请求参数 | 无 |
| 返回结果 | `loading.html` |
| Demo | `http://127.0.0.1:5000/loading` |

## 7. 状态码汇总

| 状态码 | 使用场景 | 当前响应格式 |
|---|---|---|
| `200` | 生成成功、导出成功、页面访问成功 | JSON / PNG / HTML |
| `302` | 表单生成成功并跳转海报 | `Location` 响应头 |
| `400` | 必填参数缺失；非法请求也可能由 Flask 默认处理 | JSON / 纯文本 / 默认 HTML |
| `404` | 海报缓存不存在或路由不存在 | JSON / 纯文本 / 默认 HTML |
| `405` | 请求方法不允许 | Flask 默认 HTML |
| `500` | DeepSeek、JSON 解析、截图或服务器内部异常 | JSON / 纯文本 / 默认 HTML |

## 8. 接口治理建议（按优先级）

| 优先级 | 建议 | 原因 |
|---|---|---|
| P0 | 新接口统一使用 `/api/v1` 与统一错误结构 | 避免继续扩大不一致的契约 |
| P0 | 对学段、学科、教材、字符串长度做服务端校验 | 当前仅判断非空，异常输入会进入模型调用 |
| P0 | 生产环境不向客户端返回原始异常文本 | 避免泄露内部路径、依赖与上游错误 |
| P0 | 将生成与导出改为异步任务或至少增加超时/限流 | 两者都可能长时间占用服务资源 |
| P1 | 增加鉴权、请求 ID、访问日志与频率限制 | 部署到公网后防止被滥用 |
| P1 | 增加 OpenAPI 文档与契约测试 | 支持真正前后端并行开发 |
| P1 | 明确缓存保留时间、容量与清理策略 | 防止 `output/` 长期膨胀 |
| P2 | 按开发/生产环境配置 CORS | 支持独立前端，同时避免全量放开 |

## 9. 现有知识卡业务的数据结构（内部缓存）

生成接口对外只返回 `poster_id`，但缓存中的 JSON 顶层结构如下，供后续联调与迁移参考：

```json
{
  "meta": {
    "grade": "七年级",
    "subject": "英语",
    "book": "上册",
    "publisher": "人教版",
    "unit_name": "Unit 1",
    "stage": "初中",
    "poster_title": "七年级上册·英语·Unit 1",
    "theme": {},
    "card_titles": []
  },
  "cards": []
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `meta` | object | 生成条件、标题、主题和卡片标题等元数据 |
| `cards` | array | DeepSeek 返回并解析后的知识卡列表 |
| `cards[].content` | string | 卡片正文；展示前会由后端转换为结构化 HTML |

> 缓存结构目前不是稳定的公开 API 契约。若独立前端需要直接渲染卡片，应新增明确的卡片查询 API，而不是读取服务器文件。
