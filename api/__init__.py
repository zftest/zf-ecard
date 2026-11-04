"""新增功能的后端接口层。

与旧版 `app.py` 里的 `/api/generate`、`/api/export/*` 完全隔离：
旧接口冻结不动（见 docs/architecture-frontend-backend-separation.md 的兼容红线），
新接口一律走 `/api/v1` 前缀，将来加鉴权、改错误结构都不会波及旧页面。
"""
