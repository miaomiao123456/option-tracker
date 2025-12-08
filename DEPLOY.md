# 部署指南 - Railway/Render免费托管

## 方式一: Railway部署 (推荐)

### 1. 准备工作
- 注册 [Railway](https://railway.app/) 账号 (支持GitHub登录)
- Fork或上传本项目到GitHub

### 2. 部署步骤

1. 登录Railway,点击 "New Project"
2. 选择 "Deploy from GitHub repo"
3. 选择你的仓库 `option_tracker`
4. Railway会自动检测Python项目并开始部署

### 3. 配置环境变量

在Railway项目设置中添加以下环境变量:

```bash
UQER_TOKEN=190bbd239ab55cb2f3f2919601622b0b793e94c35d7967e0c4b325682eddd981
DATABASE_URL=sqlite:///./option_tracker.db
DEBUG=False
LOG_LEVEL=INFO
```

### 4. 获取公网地址

部署完成后,Railway会自动分配一个域名,格式类似:
- `https://option-tracker-production-xxxx.up.railway.app`

### 5. 测试访问

- API文档: `https://your-domain.up.railway.app/docs`
- 前端页面: `https://your-domain.up.railway.app/frontend`

---

## 方式二: Render部署

### 1. 准备工作
- 注册 [Render](https://render.com/) 账号
- 将项目推送到GitHub

### 2. 部署步骤

1. 登录Render,点击 "New +"
2. 选择 "Web Service"
3. 连接GitHub仓库
4. 配置如下:
   - **Name**: option-tracker
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 3. 配置环境变量

添加以下环境变量:

```bash
UQER_TOKEN=190bbd239ab55cb2f3f2919601622b0b793e94c35d7967e0c4b325682eddd981
DATABASE_URL=sqlite:///./option_tracker.db
DEBUG=False
LOG_LEVEL=INFO
PORT=8000
```

### 4. 部署完成

Render会给你一个域名,格式类似:
- `https://option-tracker.onrender.com`

---

## 注意事项

### 1. Playwright浏览器问题
免费托管服务通常不支持Playwright的浏览器安装。需要修改依赖的爬虫:
- ✅ 优矿SDK爬虫正常工作 (不需要浏览器)
- ❌ 需要Playwright的爬虫可能无法使用

### 2. 定时任务
免费服务可能会在无访问时休眠,定时任务可能不会按时执行。建议:
- 使用外部定时服务(如GitHub Actions)定期访问API触发更新
- 或升级到付费版本保持服务运行

### 3. 数据持久化
SQLite数据库文件会在每次重新部署时丢失。建议:
- 方案1: 使用Railway提供的持久化存储
- 方案2: 切换到PostgreSQL数据库(Render/Railway都提供免费PostgreSQL)

### 4. 免费额度
- **Railway**: 每月500小时免费运行时间,5GB存储
- **Render**: 每月750小时免费运行时间,但服务会在15分钟无访问后休眠

---

## 快速开始

如果你只是想快速测试,可以使用Railway一键部署:

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template)

部署完成后记得在环境变量中设置 `UQER_TOKEN`!
