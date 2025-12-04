# Cookies登录使用指南

## 📌 为什么使用Cookies

智汇期讯和融达数据的登录页面使用了复杂的前端框架（可能包括iframe、动态加载等），自动化登录较为困难。因此我们采用**手动登录一次，保存cookies复用**的方案。

## 🚀 快速开始

### 步骤1：手动登录并保存cookies

运行cookies保存工具：

```bash
cd /Users/pm/Documents/期权交易策略/option_tracker
python3 save_cookies.py
```

选择要保存cookies的网站：
- 选项1: 智汇期讯
- 选项2: 融达数据
- 选项3: 两个都保存（推荐）

### 步骤2：在打开的浏览器中手动登录

程序会打开浏览器窗口，请在浏览器中：
1. 输入账号密码
2. 完成验证（如果有）
3. 确认登录成功

### 步骤3：保存cookies

登录成功后，在控制台输入 `y` 并回车，程序会自动保存cookies。

### 步骤4：验证cookies

cookies会保存到：
- 智汇期讯: `option_tracker/.cookies/zhihui_cookies.json`
- 融达数据: `option_tracker/.cookies/rongda_cookies.json`

现在爬虫会自动使用这些cookies登录！

## 🔄 Cookies有效期

Cookies通常有效期为7-30天。当cookies失效时：
- 爬虫会提示"cookies已失效或不存在"
- 重新运行 `python3 save_cookies.py` 更新cookies即可

## 🛠️ 测试cookies是否有效

运行测试脚本：

```bash
python3 test_fixed_crawlers.py
```

如果看到"✅ cookies有效，已自动登录"，说明cookies正常工作。

## ⚠️ 注意事项

1. **保护cookies安全**
   - cookies文件包含登录凭证，不要分享给他人
   - 已添加到.gitignore，不会被git跟踪

2. **账号信息**
   - 账号: 18321399574
   - 密码: yi2013405
   - 两个网站使用相同账号密码

3. **Cookies过期处理**
   - cookies过期后爬虫会自动提示
   - 重新保存cookies即可，无需修改代码

## 📝 示例输出

### 保存cookies成功
```
✅ cookies已保存到: /Users/pm/Documents/期权交易策略/option_tracker/.cookies/zhihui_cookies.json
   共保存 12 个cookies
```

### 使用cookies登录成功
```
已加载cookies: 12个
cookies已注入到浏览器
浏览器初始化成功
开始登录智汇期讯...
✅ cookies有效，已自动登录
```

### Cookies失效
```
cookies已失效或不存在，需要重新登录
请运行 'python3 save_cookies.py' 手动登录并保存cookies
```

## 🔧 故障排除

### 问题1: 保存cookies后仍然登录失败

**解决方案**:
- 检查cookies文件是否存在
- 确认手动登录时已经完全登录成功
- 尝试重新保存cookies

### 问题2: 浏览器没有打开

**解决方案**:
- 确保已安装playwright: `pip install playwright`
- 运行: `playwright install chromium`

### 问题3: cookies文件找不到

**解决方案**:
- 检查.cookies目录是否存在
- 运行save_cookies.py时确认输入了'y'保存
