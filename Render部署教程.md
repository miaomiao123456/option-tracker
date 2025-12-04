# 🚀 Render.com 部署教程（完全免费）

## ✅ 免费套餐内容
- 750小时/月运行时间
- 512MB RAM
- 自动HTTPS证书
- 持续部署（Git推送自动更新）
- 完全免费，无需信用卡

---

## 📝 部署步骤（10分钟完成）

### 第一步：创建 GitHub 仓库

1. **访问 GitHub**
   - 打开：https://github.com/new
   - 仓库名：`option-tracker`（或任意名称）
   - 选择：Public（公开）
   - 点击：Create repository

2. **推送代码到 GitHub**
   ```bash
   cd /Users/pm/Documents/期权交易策略/option_tracker

   # 添加远程仓库（替换成你的GitHub用户名）
   git remote add origin https://github.com/YOUR_USERNAME/option-tracker.git

   # 推送代码
   git branch -M main
   git push -u origin main
   ```

---

### 第二步：注册 Render.com

1. **访问 Render.com**
   - 打开：https://render.com/
   - 点击：Get Started
   - 使用 GitHub 账号登录（推荐）

2. **授权 GitHub**
   - Render 会请求访问你的 GitHub 仓库
   - 点击：Authorize Render

---

### 第三步：创建 Web Service

1. **新建服务**
   - 在 Dashboard 点击：New +
   - 选择：Web Service

2. **连接仓库**
   - 找到你的仓库：`option-tracker`
   - 点击：Connect

3. **配置服务**（会自动识别 render.yaml）
   - **Name**: `option-alpha-api`（或任意名称）
   - **Region**: Oregon（美国俄勒冈）
   - **Branch**: main
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

4. **配置环境变量**
   点击 "Advanced" → 添加环境变量：

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | `sqlite:///./option_tracker.db` |
   | `JYK_USER` | `18321399574` |
   | `JYK_PASS` | `yi2013405` |
   | `GEMINI_API_KEY` | `sk-IJhu2VBNt2G97XJeE6F82dD8047c4a2989326250068aA1F5` |
   | `GEMINI_BASE_URL` | `https://www.apillm.online/v1` |
   | `DEBUG` | `false` |

5. **选择计划**
   - 选择：Free（免费）
   - 点击：Create Web Service

---

### 第四步：等待部署

部署过程约需 **5-10分钟**：

```
✓ 克隆仓库
✓ 安装依赖
✓ 构建应用
✓ 启动服务
```

部署成功后，你会看到：
- ✅ Service is live
- 🌐 URL: `https://option-alpha-api.onrender.com`

---

### 第五步：测试 API

1. **访问 API 文档**
   ```
   https://your-app.onrender.com/docs
   ```

2. **测试健康检查**
   ```
   https://your-app.onrender.com/health
   ```

3. **测试总览接口**
   ```
   https://your-app.onrender.com/api/v1/summary/overview
   ```

---

### 第六步：修改前端配置

编辑 `frontend.html` 第 164 行：

```javascript
// 修改前
const API_BASE = 'http://localhost:8000/api/v1';

// 修改后（替换成你的Render URL）
const API_BASE = 'https://your-app.onrender.com/api/v1';
```

---

## 🎨 部署前端到 Netlify（免费）

### 方式1：拖拽部署
1. 访问：https://app.netlify.com/drop
2. 拖拽 `frontend.html` 到页面
3. 自动部署完成！

### 方式2：连接 GitHub
1. 登录 Netlify
2. New Site → Import from Git
3. 选择你的仓库
4. Publish directory: `.`
5. 点击 Deploy

**你的前端地址：** `https://your-site.netlify.app`

---

## ⚠️ 重要注意事项

### 1. Render 免费版限制

- **休眠机制**：15分钟无请求会自动休眠
- **唤醒时间**：首次请求需要等待 15-30 秒
- **解决方案**：使用 UptimeRobot 定时ping保持唤醒

### 2. 爬虫建议

由于 Render 免费版资源有限，**建议爬虫在本地运行**：

```bash
# 本地运行爬虫定时任务
cd /Users/pm/Documents/期权交易策略/option_tracker

# 只启动爬虫，不启动API
python -c "from app.scheduler import *; init_scheduler(); start_scheduler(); import time; time.sleep(86400)"
```

### 3. 数据库持久化

Render 免费版重启会丢失数据，建议：
- 使用 Supabase 免费 PostgreSQL
- 或使用 PlanetScale 免费 MySQL

---

## 🔧 故障排查

### 问题1：部署失败
```bash
# 查看构建日志
Render Dashboard → Logs → Build logs
```

常见错误：
- 缺少依赖 → 检查 `requirements.txt`
- Python版本 → 添加 `runtime.txt` 指定版本

### 问题2：API无法访问
检查：
1. 服务是否 Live
2. 环境变量是否配置
3. CORS设置是否正确

### 问题3：首次请求慢
- 这是正常的（冷启动需要 15-30 秒）
- 使用 UptimeRobot 保持唤醒

---

## 📊 配置持续部署

每次推送代码到 GitHub，Render 会自动重新部署：

```bash
# 修改代码后
git add .
git commit -m "Update feature"
git push

# Render 自动检测并部署
```

---

## 🎁 免费保持唤醒（可选）

### 使用 UptimeRobot

1. 注册：https://uptimerobot.com/
2. 添加监控：
   - Type: HTTP(s)
   - URL: `https://your-app.onrender.com/health`
   - Interval: 5 分钟
3. Render 会保持常驻内存

---

## 💰 完整免费方案总结

| 服务 | 用途 | 成本 |
|------|------|------|
| Render.com | API 后端 | $0 |
| Netlify | 前端托管 | $0 |
| Supabase | PostgreSQL 数据库（可选）| $0 |
| UptimeRobot | 保持唤醒（可选）| $0 |
| GitHub | 代码托管 | $0 |

**总成本：$0/月**

---

## 🚀 快速命令集合

```bash
# 1. 推送到 GitHub
git add .
git commit -m "Update"
git push

# 2. 查看 Render 日志
curl https://your-app.onrender.com/health

# 3. 测试 API
curl https://your-app.onrender.com/api/v1/summary/overview
```

---

## ✅ 部署完成检查清单

- [ ] GitHub 仓库创建成功
- [ ] 代码推送到 GitHub
- [ ] Render 服务创建成功
- [ ] 环境变量配置完成
- [ ] API 可以访问
- [ ] 前端部署到 Netlify
- [ ] 前端 API 地址已修改
- [ ] （可选）配置 UptimeRobot

---

## 🎊 完成！

你的 API 现在可以通过以下地址访问：

- **API 文档**: https://your-app.onrender.com/docs
- **健康检查**: https://your-app.onrender.com/health
- **前端页面**: https://your-site.netlify.app

完全免费，自带 HTTPS，全球 CDN 加速！🚀

---

**需要帮助？**
- Render 文档：https://render.com/docs
- Netlify 文档：https://docs.netlify.com/
