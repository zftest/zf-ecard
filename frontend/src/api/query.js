/**
 * 查询参数的规范化。
 *
 * 需要它的原因很具体：axios 会把 `null` 序列化成字符串 "null" 发给后端，
 * 于是 `?theme=null` 变成了"筛选主题叫 null 的词"，返回空列表。
 * 而页面里 tab 切换、筛选清空这类场景，值天然就是 null / 空数组。
 *
 * 规则：
 *   null / undefined / '' → 整个 key 丢掉
 *   数组                 → 英文逗号拼接（与后端 WordListQuery 的约定一致）
 *   其余                 → 原样透传，交给 axios 序列化
 */
export function cleanParams(params = {}) {
  const result = {}

  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === '') continue

    if (Array.isArray(value)) {
      const parts = value.filter((item) => item !== null && item !== undefined && item !== '')
      if (parts.length === 0) continue
      result[key] = parts.join(',')
      continue
    }

    // 布尔值必须显式转成字符串：axios 会跳过 false 吗？不会，
    // 但后端 pydantic 对 "false" 能正确解析成 False，对 "" 不能。
    result[key] = typeof value === 'boolean' ? String(value) : value
  }

  return result
}
