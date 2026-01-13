# 阿里云部署快速参考

## 🎯 最快5分钟部署

### 前提条件
✅ 阿里云ECS服务器 (2核4G, Ubuntu 22.04)
✅ 公网IP已配置
✅ 安全组开放 22, 8001 端口

### 一键部署命令

```bash
# 1. SSH连接服务器
ssh root@your-server-ip

# 2. 运行部署脚本
bash <(curl -s https://raw.githubusercontent.com/your-repo/main/deploy_aliyun.sh)

# 3. 上传代码 (本地执行)
scp -r /path/to/option_tracker/* root@your-server-ip:/opt/option-tracker/

# 4. 配置环境变量 (服务器执行)
nano /opt/option-tracker/.env.production
# 填入 UQER_TOKEN

# 5. 启动服务
cd /opt/option-tracker
docker compose -f docker-compose.prod.yml up -d --build

# 6. 访问
http://your-server-ip:8001/frontend.html
```

## 📋 关键配置

### 环境变量 (.env.production)
```env
UQER_TOKEN=your_token_here          # 必填 - 优矿Token
DATABASE_URL=sqlite:///./data/option_tracker.db
DEBUG=False
PORT=8001
```

### 安全组规则
| 端口 | 协议 | 用途 | 源地址 |
|-----|------|------|--------|
| 22 | TCP | SSH | 你的IP |
| 8001 | TCP | 应用 | 0.0.0.0/0 |

## 🔧 常用命令

```bash
# 查看状态
docker ps
docker compose -f docker-compose.prod.yml logs -f

# 重启服务
docker compose -f docker-compose.prod.yml restart

# 停止服务
docker compose -f docker-compose.prod.yml stop

# 更新代码
git pull
docker compose -f docker-compose.prod.yml up -d --build

# 备份数据库
cp option_tracker.db backup_$(date +%Y%m%d).db
```

## 🌐 配置域名 (可选)

### 1. 添加DNS记录
```
类型: A
主机: @ 或 option
值: your-server-ip
```

### 2. 安装Nginx + SSL
```bash
# 安装
sudo apt install -y nginx certbot python3-certbot-nginx

# 配置 (见 DEPLOY_ALIYUN.md)
sudo nano /etc/nginx/sites-available/option-tracker

# 获取SSL证书
sudo certbot --nginx -d your-domain.com
```

### 3. 访问
```
https://your-domain.com
```

## ❌ 故障排查

### 问题: 容器无法启动
```bash
docker compose -f docker-compose.prod.yml logs
docker system prune -a
```

### 问题: 端口被占用
```bash
sudo lsof -i :8001
sudo kill -9 <PID>
```

### 问题: 内存不足
```bash
free -h
docker stats
# 升级到更大规格的ECS
```

## 📞 需要帮助?

详细文档: `DEPLOY_ALIYUN.md`
项目文档: `README.md`

---

**预计费用**: ¥50-100/月 (2核4G ECS + 公网带宽)
