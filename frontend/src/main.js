import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import { setErrorListener } from '@/api/client'
import { toast } from '@/composables/useToast'
import '@/styles/index.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)

/**
 * 把 axios 拦截器里的错误接到 Toast 上。
 *
 * 这一步必须在 mount 之前做：如果放在某个组件的 onMounted 里，
 * 首个页面自己的初始化请求失败时监听器还没注册，错误会被静默吞掉 ——
 * 表现为"打开首页一片空白，控制台什么也没有"。
 *
 * 拦截器已经过滤掉 silent 类错误（AUDIO_NOT_AVAILABLE 等），
 * 所以这里拿到的都是真该告诉用户的。
 */
setErrorListener((normalized) => {
  toast.error(normalized.message, {
    detail: normalized.requestId ? `问题编号 ${normalized.requestId}` : '',
  })
})

/**
 * 兜底的组件异常。
 *
 * 不弹堆栈给用户（那是泄漏内部实现），只给一句可执行的提示；
 * 详细信息进控制台，供开发者排查。
 */
app.config.errorHandler = (err, _instance, info) => {
  console.error('[vue] 未捕获的组件异常：', info, err)
  toast.error('页面出了点问题，刷新一下再试')
}

app.mount('#app')
