# 词练 · 前端

Vue 3 + Vite 的单页应用，构建产物由 Flask 挂在 `/app/` 下，与旧的 Jinja 页面共存。

## 技术栈

| 层 | 选型 | 版本 |
|---|---|---|
| 框架 | Vue | 3.5 |
| 构建 | Vite | 8.3 |
| 路由 | Vue Router（history 模式，base `/app/`） | 5.4 |
| 状态 | Pinia（setup store 写法） | 4.1 |
| HTTP | axios（统一拦截器 + 错误归一化） | 1.21 |

> 版本要求：Node ≥ 20.19（Vite 8 的硬性要求）。本机实测 22.22 可用。

## 开发

```bash
cd frontend
npm install
npm run dev          # http://127.0.0.1:5173
```

开发期 `/api` 由 Vite 代理到 `http://127.0.0.1:5000`，浏览器里始终同源，**不需要后端开 CORS**。

后端不在 5000 端口时，用环境变量指定：

```bash
VITE_API_TARGET=http://127.0.0.1:5058 npm run dev
```

## 构建与部署

```bash
npm run build        # 产物 -> frontend/dist
```

构建完直接访问 `http://127.0.0.1:5000/app/` 即可，Flask 的 `spa.py` 会自动托管。

**产物不进 Git**（`.gitignore` 里忽略 `frontend/dist/`）。换台机器 clone 下来必须先 `npm run build`，否则 `/app/` 会显示一张"前端还没有构建"的说明页 —— 这是刻意做的，比 404 更能说明问题。

## 目录结构

```
src/
├── api/              # 接口层，页面不直接 import axios
│   ├── client.js     # 实例 + 拦截器 + 重试策略
│   ├── errors.js     # 错误码 -> 中文文案，白名单静默
│   ├── query.js      # 查询参数规范化（null/数组）
│   └── words.js / practice.js / wrongbook.js / learners.js / audio.js / system.js
├── components/       # 8 个基础组件 + PageStub（占位页）
├── composables/
│   └── useToast.js   # 模块级单例，供拦截器调用
├── router/
│   ├── index.js      # 8 条路由，全部懒加载
│   └── navigation.js # 侧栏/底部标签读同一份配置
├── stores/           # learner / catalog / practice / wrongbook
├── styles/
│   ├── tokens.css    # 设计令牌，唯一的颜色来源
│   ├── base.css      # reset + reduce-motion 降级
│   └── index.css     # 入口，顺序不能换
└── views/            # 8 个页面
```

## 三条硬约定

**1. 颜色只写在 `tokens.css`。**

组件里出现 `#2457c5` 这种字面色值就是 bug。日后加暗色主题只需覆盖同名变量，组件零改动。

**2. 页面不直接 `import axios`。**

必须走 `api/*.js`。绕过 client 就等于绕过拦截器，错误提示和重试策略会各写一套。

**3. 触控目标 ≥ 44px。**

`AppButton size="sm"` 的视觉高度是 36px，但用 `::after` 伪元素把命中区扩到 44px。看起来紧凑，实际点得中。

## 基础组件

| 组件 | 主要 props | 无障碍要点 |
|---|---|---|
| `AppButton` | `variant` primary/secondary/ghost/text/danger、`size`、`loading`、`block` | 原生 `<button>`，Enter/Space 直接可用；`loading` 时 `aria-busy` + 禁用防连点 |
| `AppInput` | `v-model`、`label`、`hint`、`error`、`size` md/lg | `<label for>` 关联、错误时 `aria-invalid` + `aria-describedby`；中文输入法选词回车不误触发提交 |
| `AppCard` | `eyebrow`、`title`、`headingLevel`、`padding`、`tone` | 标题层级可调，避免 h1 → h3 跳级 |
| `AppChip` | `selectable`、`selected`、`tone` | 可选中时 `role="checkbox"` + `aria-checked`；只读时渲染 `<span>`（不能点的东西不做成 button） |
| `AppDialog` | `v-model`、`title`、`size`、`closeOnBackdrop/Esc` | 原生 `<dialog>` + `showModal()`，焦点陷阱/inert/焦点还原都是浏览器保证的 |
| `AppToast` | 无（读 `useToast()` 单例） | 容器 `aria-live="polite"`；错误项 `role="alert"` 打断；错误不自动消失（要看清 request_id） |
| `AppProgressBar` | `value`、`max`、`tone`、`indeterminate` | `role="progressbar"` + `aria-valuenow/min/max` |
| `AppEmptyState` | `mark`、`title`、`description`、`compact` | 空状态必须说清"为什么空"和"下一步做什么" |

## 已知取舍

**写操作不自动重试。** 通用实践是「5xx 重试 3 次」，这里刻意只重试 GET。
原因：`POST /practice/sessions` 重试会建出两个会话，孩子的作答记录被劈成两半。
5xx 对写操作的做法是把错误如实告诉用户，由他点"重试" —— 用户主动点的那次语义清晰，不会产生隐藏的重复副作用。见 `api/client.js` 的 `isRetryable`。

**没有引入 `pinia-plugin-persistedstate`。** 只有 `learner_id` 一个字段需要持久化，为此加一个依赖不划算，手写 6 行 `localStorage` 读写即可（含隐私模式的 `try/catch`）。

**`AUDIO_NOT_AVAILABLE` 不弹 Toast。** 它不是错误，是"这个词没录音"的正常信号。前端应切到设备语音并标注「设备语音（演示）」。在 `api/errors.js` 的 `SILENT_CODES` 里。

## 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 构建后页面全白、控制台无报错 | `vite.config.js` 的 `base` 不是 `/app/`，资源请求 404 | 改 `base: '/app/'` 重新构建 |
| 控制台 `Unexpected token '<'` | 缺失的 `.js` 被回落成 index.html | `spa.py` 已按后缀区分，缺资源直接 404 |
| 刷新 `/app/words` 得到 404 | 服务端没做 history 回落 | 检查 `spa.py` 是否注册 |
| 控制台一条 favicon 404 | 没写 `<link rel="icon">` | `index.html` 里已内联 SVG 图标 |
| `http://127.0.0.1:5173` 打不开、`localhost:5173` 能开 | Vite 默认 host 是 `localhost`，Node 18+ 优先解析成 IPv6 `::1` | `vite.config.js` 已固定 `host: '127.0.0.1'` |
| `npm install` 卡住或 502 | 环境变量里有坏代理 | `env -u http_proxy -u https_proxy npm install` |
