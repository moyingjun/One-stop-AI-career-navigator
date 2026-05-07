import { createApp } from 'vue'
import './style.css'

// 🌟 徒弟看这里，这就是咱们给移动端加的“救命补丁”
// 如果浏览器不认识 toHex，咱们就手把手教它怎么做
if (typeof Uint8Array.prototype.toHex !== 'function') {
  console.log('检测到环境不支持 toHex，正在注入补丁...');
  Uint8Array.prototype.toHex = function () {
    return Array.from(this)
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
  };
}

import App from './App.vue'
import router from './router'

createApp(App)
  .use(router)
  .mount('#app')