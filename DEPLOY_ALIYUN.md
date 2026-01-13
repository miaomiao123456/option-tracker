# 阿里云部署指南

## 📋 前置准备

### 1. 阿里云ECS实例要求

- **配置建议**:
  - CPU: 2核以上
  - 内存: 4GB以上
  - 存储: 40GB以上
  - 操作系统: Ubuntu 22.04 或 CentOS 8

- **网络配置**:
  - 公网IP (弹性公网IP)
  - 安全组开放端口: 22 (SSH), 8001 (应用)

### 2. 购买和配置ECS

1. 登录阿里云控制台: https://ecs.console.aliyun.com
2. 点击"创建实例"
3. 选择配置:
   - 地域: 就近选择 (如 华东2-上海)
   - 实例规格: ecs.t6-c1m2.large (2核4G)
   - 镜像: Ubuntu 22.04 64位
   - 存储: 系统盘 40GB
   - 网络: 分配公网IP,带宽按需选择
4. 设置安全组规则:
   ```
   入方向规则:
   - 端口 22/TCP (SSH)
   - 端口 8001/TCP (应用访问)
   - 源地址: 0.0.0.0/0
   ```

## 🚀 快速部署 (推荐)

### 方式一: 使用一键部署脚本

1. **连接到服务器**
```bash
ssh root@your-server-ip
```

2. **下载部署脚本**
```bash
# 创建项目目录
mkdir -p /opt/option-tracker
cd /opt/option-tracker

# 下载部署脚本
curl -o deploy_aliyun.sh https://your-repo/deploy_aliyun.sh
chmod +x deploy_aliyun.sh

# 运行脚本
./deploy_aliyun.sh
```

3. **上传项目代码**

从本地上传到服务器:
```bash
# 在本地终端执行
scp -r /Users/pm/Documents/期权交易策略/option_tracker/* root@your-server-ip:/opt/option-tracker/
```

或使用Git:
```bash
# 在服务器上执行
cd /opt/option-tracker
git clone <your-repo-url> .
```

4. **配置环境变量**
```bash
nano /opt/option-tracker/.env.production

# 重要: 填入你的配置
# - UQER_TOKEN: 优矿API Token
# - GEMINI_API_KEY: AI API Key (选填)
```

5. **启动服务**
```bash
cd /opt/option-tracker
docker compose -f docker-compose.prod.yml up -d --build
```

6. **验证部署**
```bash
# 查看容器状态
docker ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f

# 测试API
curl http://localhost:8001/health
```

7. **访问应用**
```
http://your-server-ip:8001/frontend.html
```

## 🔧 手动部署 (详细步骤)

### 第一步: 安装Docker

**Ubuntu/Debian:**
```bash
# 更新包管理器
sudo apt-get update

# 安装依赖
sudo apt-get install -y ca-certificates curl gnupg

# 添加Docker官方GPG密钥
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 添加Docker仓库
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 启动Docker
sudo systemctl start docker
sudo systemctl enable docker
```

**CentOS/RHEL:**
```bash
# 安装依赖
sudo yum install -y yum-utils

# 添加Docker仓库
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 安装Docker
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 启动Docker
sudo systemctl start docker
sudo systemctl enable docker
```

### 第二步: 上传代码

```bash
# 创建项目目录
mkdir -p /opt/option-tracker
cd /opt/option-tracker

# 从本地上传 (在本地执行)
scp -r /Users/pm/Documents/期权交易策略/option_tracker/* root@your-server-ip:/opt/option-tracker/

# 或使用Git
git clone <your-repo-url> .
```

### 第三步: 配置环境

```bash
# 复制并编辑生产环境配置
cp .env.example .env.production
nano .env.production
```

最小配置:
```env
DATABASE_URL=sqlite:///./data/option_tracker.db
UQER_TOKEN=your_uqer_token_here
DEBUG=False
LOG_LEVEL=INFO
PORT=8001
```

### 第四步: 构建和启动

```bash
# 构建Docker镜像
docker compose -f docker-compose.prod.yml build

# 启动服务
docker compose -f docker-compose.prod.yml up -d

# 查看日志
docker compose -f docker-compose.prod.yml logs -f
```

### 第五步: 配置防火墙

**Ubuntu (UFW):**
```bash
sudo ufw allow 22/tcp
sudo ufw allow 8001/tcp
sudo ufw enable
```

**CentOS (firewalld):**
```bash
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --permanent --add-port=8001/tcp
sudo firewall-cmd --reload
```

## 🔒 使用域名和HTTPS (推荐)

### 1. 配置域名

在域名服务商添加A记录:
```
类型: A
主机记录: option (或 @)
记录值: your-server-ip
TTL: 600
```

### 2. 安装Nginx

```bash
# Ubuntu
sudo apt-get install -y nginx

# CentOS
sudo yum install -y nginx
```

### 3. 配置Nginx反向代理

创建配置文件:
```bash
sudo nano /etc/nginx/sites-available/option-tracker
```

配置内容:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

启用配置:
```bash
# Ubuntu
sudo ln -s /etc/nginx/sites-available/option-tracker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# CentOS
sudo cp /etc/nginx/sites-available/option-tracker /etc/nginx/conf.d/option-tracker.conf
sudo nginx -t
sudo systemctl restart nginx
```

### 4. 安装SSL证书 (Let's Encrypt)

```bash
# 安装certbot
sudo apt-get install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

现在可以通过 `https://your-domain.com` 访问!

## 📊 运维管理

### 查看服务状态
```bash
docker ps
docker compose -f docker-compose.prod.yml ps
```

### 查看日志
```bash
# 实时日志
docker compose -f docker-compose.prod.yml logs -f

# 最近100行
docker compose -f docker-compose.prod.yml logs --tail=100

# 特定服务
docker logs option-tracker
```

### 重启服务
```bash
docker compose -f docker-compose.prod.yml restart
```

### 停止服务
```bash
docker compose -f docker-compose.prod.yml stop
```

### 更新代码
```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker compose -f docker-compose.prod.yml up -d --build
```

### 备份数据库
```bash
# 备份SQLite数据库
cp option_tracker.db option_tracker_backup_$(date +%Y%m%d).db

# 或使用Docker卷
docker run --rm \
  -v option-tracker_data:/data \
  -v $(pwd):/backup \
  ubuntu tar czf /backup/data-backup-$(date +%Y%m%d).tar.gz /data
```

## 🐛 常见问题

### 1. 端口被占用
```bash
# 查看端口占用
sudo lsof -i :8001
sudo netstat -tulpn | grep 8001

# 停止占用进程
sudo kill -9 <PID>
```

### 2. Docker权限问题
```bash
# 将当前用户加入docker组
sudo usermod -aG docker $USER
newgrp docker
```

### 3. 容器启动失败
```bash
# 查看详细错误
docker compose -f docker-compose.prod.yml logs

# 进入容器调试
docker exec -it option-tracker bash
```

### 4. 数据库初始化
```bash
# 进入容器
docker exec -it option-tracker bash

# 手动初始化
python -c "from app.models.database import init_db; init_db()"
```

### 5. 内存不足
```bash
# 查看内存使用
free -h
docker stats

# 清理Docker
docker system prune -a
```

## 📈 性能优化

### 1. 调整Worker数量
编辑 `.env.production`:
```env
WORKERS=4  # 建议CPU核心数
```

### 2. 启用Redis缓存
```bash
# 安装Redis
sudo apt-get install -y redis-server

# 配置
REDIS_URL=redis://localhost:6379/0
```

### 3. 使用MySQL数据库
```env
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/option_tracker
```

## 🔐 安全建议

1. **修改默认端口**: 不要使用默认的22端口
2. **使用密钥登录**: 禁用密码登录
3. **配置防火墙**: 只开放必要端口
4. **定期更新**: 及时更新系统和Docker
5. **使用HTTPS**: 强制使用SSL证书
6. **限制访问**: 配置IP白名单

## 📞 技术支持

- 文档: 查看项目README.md
- Issues: 提交到GitHub Issues
- 日志: 检查 `/opt/option-tracker/logs/`

---

**部署完成后访问**: `http://your-server-ip:8001/frontend.html`

或配置域名后访问: `https://your-domain.com`
