# 📝 手动保存Cookies操作指南

## 当前状态
- ✅ 3个爬虫正常工作: 方期看盘, Openvlab, 交易可查
- ⚠️ 2个爬虫需要cookies: 智汇期讯, 融达数据

## 为什么需要手动保存Cookies?

智汇期讯和融达数据的登录页面使用了复杂的前端框架（动态modal对话框），自动化登录比较困难。最可靠的方案是**手动登录一次，然后让系统复用cookies**。

## 📱 方案一：使用Chrome浏览器手动保存 (推荐)

### 步骤 1: 准备浏览器
1. 打开Chrome浏览器
2. 按F12打开开发者工具

### 步骤 2: 登录智汇期讯
1. 访问: https://hzzhqx.com/home
2. 点击页面右上角的「登录」按钮
3. 在弹出的登录框中输入:
   - 账号: `18321399574`
   - 密码: `yi2013405`
4. 点击登录
5. 确认登录成功（页面右上角显示用户信息）

### 步骤 3: 导出Cookies
1. 在开发者工具中，切换到「Application」标签页
2. 左侧找到「Storage」->「Cookies」->「https://hzzhqx.com」
3. 右键点击任意cookie，选择「Copy all as JSON」或逐个复制
4. 将复制的内容保存到文件:
   ```
   /Users/pm/Documents/期权交易策略/option_tracker/.cookies/zhihui_cookies.json
   ```

### 步骤 4: 重复操作保存融达数据Cookies
1. 访问: https://dt.rongdaqh.com/finance_and_economics/calendar
2. 登录 (账号密码相同)
3. 导出Cookies到:
   ```
   /Users/pm/Documents/期权交易策略/option_tracker/.cookies/rongda_cookies.json
   ```

---

## 🤖 方案二：使用自动化脚本 (需要手动交互)

运行以下命令，浏览器会自动打开，你只需要在浏览器中完成登录即可:

```bash
cd /Users/pm/Documents/期权交易策略/option_tracker
python3 save_cookies_smart.py
```

脚本会:
1. 依次打开两个网站的浏览器窗口
2. 等待你在浏览器中手动登录
3. 检测到登录成功后，自动保存cookies
4. 最多等待5分钟

**重要**:
- 浏览器打开后，请在窗口中完成登录操作
- 不要关闭浏览器，等待脚本自动检测并保存cookies

---

## ✅ 验证Cookies是否有效

保存cookies后，运行测试脚本:

```bash
python3 run_all_crawlers.py
```

查看输出，应该显示:
```
✅ cookies有效，已自动登录
```

---

## 🔄 Cookies过期处理

Cookies通常有效期为7-30天。当cookies过期时:
- 爬虫会提示 "cookies已失效或不存在"
- 重新执行上述步骤保存新的cookies即可

---

## 📝 cookies文件格式示例

正确的cookies文件应该是JSON数组格式，类似:

```json
[
  {
    "name": "session_id",
    "value": "eyJhbGciOiJI...",
    "domain": ".hzzhqx.com",
    "path": "/",
    "expires": 1735209600,
    "httpOnly": true,
    "secure": true,
    "sameSite": "Lax"
  },
  {
    "name": "token",
    "value": "Bearer abc123...",
    ...
  }
]
```

如果文件只有 `[]`（空数组），说明cookies没有保存成功。

---

## 🆘 需要帮助?

如果遇到问题:
1. 确认账号密码正确: 18321399574 / yi2013405
2. 检查cookies文件是否存在且不为空
3. 尝试重新登录并保存cookies
4. 查看爬虫日志了解详细错误信息
