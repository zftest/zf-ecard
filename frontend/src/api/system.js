import { api } from './client'

/**
 * 系统状态。首页用它做一次"后端是否连得上"的自检。
 *
 * 单独一个文件而不是塞进 words.js：它是运维视角的接口，
 * 与词库业务无关，将来加 /ready、/version 也应该落在这里。
 */
export function getHealth() {
  return api.get('/health')
}
