# 灵枢 SenseHub 阿里云部署指南（Ubuntu 22.04）

> **文档版本**：v1.0（商业化交付版）

面向场景：**外网展示官网 + 控制台 + Studio 对话 + 用户注册登录**；摄像头 / 语音 / 桌面操控可在服务器侧按需关闭，前端保持完整产品线入口。

---

## 1. 你的配置够不够？

| 项目 | 你的配置 | 结论 |
|------|----------|------|
| CPU | 2 vCPU | 够用（对话走云端 LLM API，不算本地推理） |
| 内存 | 2 GiB | **偏紧但可行**；建议加 2GB swap |
| 系统盘 | 40 GB | 够用（不下载 YOLO/Whisper 本地权重时约占 5–8 GB） |
| 带宽 | 200 Mbps 峰值 | 远超展示站 + 文本对话需求 |
| 系统 | Ubuntu 22.04 | 推荐 |

**总结：可以部署。** 关键是：

- 对话依赖 **硅基流动 / 火山方舟等 API Key**（云端推理），不在服务器跑大模型。
- 不要在这台机器上装 Playwright Chromium、YOLO 权重（省内存）。
- 用 **Nginx 反代 + HTTPS**，后端只监听 `127.0.0.1:8765`。

---

## 2. 推荐架构

```
用户浏览器
    │  HTTPS :443
    ▼
Nginx（静态前端 dist + 反代 /api /ws /health）
    │  http://127.0.0.1:8765
    ▼
sensehub FastAPI（systemd 常驻）
    │
    ├── SQLite（用户、积分、会话）
    └── 出站 HTTPS → SiliconFlow / Volcengine（对话）
```

同一域名访问时 **无跨域问题**；`LanAccessMiddleware` 看到来源为 `127.0.0.1`（Nginx 反代），可正常放行。

---

## 3. 服务器上能做什么 / 不能做什么

| 功能 | 公网演示 |
|------|----------|
| 首页、Token Plan、文档、登录注册 | ✅ |
| 积分中心、个人中心、admin 发积分 | ✅ |
| **Studio 对话**（`/studio`） | ✅（需配置 LLM API） |
| Claw 桌面指令、截图、打开记事本 | ❌（依赖 Windows 桌面） |
| 摄像头、麦克风、虚拟屏 | ❌（服务器无设备；界面可保留，点开会失败或空） |

对客户说明：外网版是「网站 + AI 对话体验」；完整多模态在你本地 Windows 演示。

---

## 4. 安全组与防火墙

阿里云轻量 **防火墙 / 安全组** 建议只开放：

- `22` SSH
- `80` HTTP（Certbot 续期 + 跳转 HTTPS）
- `443` HTTPS

**不要**把 `8765` 直接暴露到公网。

---

## 5. 一键命令清单（SSH 登录后）

### 5.1 系统依赖

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git nginx certbot python3-venv python3-pip nodejs npm

# 2GB 内存建议加 swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Node 若版本低于 20，请用 [NodeSource](https://github.com/nodesource/distributions) 安装 20+。

### 5.2 拉代码

```bash
sudo mkdir -p /opt/sensehub
sudo chown $USER:$USER /opt/sensehub
cd /opt/sensehub
git clone <你的仓库地址> .
```

### 5.3 后端配置

```bash
cp config/local.env.example config/local.env
cp config/models.yaml.example config/models.yaml
cp config/policies.yaml.example config/policies.yaml
mkdir -p /opt/sensehub/data/db /opt/sensehub/data/screenshots
```

编辑 `config/local.env`（生产示例）：

```env
SENSEHUB_ROOT=/opt/sensehub
DATA_ROOT=/opt/sensehub/data
SQLITE_PATH=/opt/sensehub/data/db/sensehub.db

API_HOST=127.0.0.1
API_PORT=8765

JWT_SECRET=<随机长字符串>
ADMIN_PASSWORD=<强密码>

SILICONFLOW_API_KEY=<你的Key>
VOLCENGINE_API_KEY=<你的Key>

USE_CUDA=false
TTS_ENABLED=false

# 注册邮箱验证码（QQ 邮箱示例）
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=你的邮箱
SMTP_PASSWORD=SMTP授权码
SMTP_FROM=你的邮箱
EMAIL_DEV_EXPOSE_CODE=false

OAUTH_FRONTEND_URL=https://你的域名
```

`config/policies.yaml` 保持 `allow_lan: false` 即可（走 Nginx 本机反代）。

### 5.4 安装后端（Linux 不装 pywin32）

```bash
cd /opt/sensehub
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
# 不要执行 playwright install（省磁盘和内存）
```

### 5.5 构建前端

```bash
cd /opt/sensehub/web
npm ci
npm run build
# 产物在 web/dist
```

### 5.6 systemd 服务

```bash
sudo tee /etc/systemd/system/sensehub.service << 'EOF'
[Unit]
Description=SenseHub Agent API
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/sensehub
Environment=PATH=/opt/sensehub/.venv/bin
ExecStart=/opt/sensehub/.venv/bin/python -m sensehub.main
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo chown -R www-data:www-data /opt/sensehub/data
sudo systemctl daemon-reload
sudo systemctl enable --now sensehub
```

### 5.7 Nginx

将 `你的域名` 替换为实际域名或服务器公网 IP（IP 访问可暂不用 HTTPS）。

```bash
sudo tee /etc/nginx/sites-available/sensehub << 'EOF'
server {
    listen 80;
    server_name 你的域名;

    root /opt/sensehub/web/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location /health {
        proxy_pass http://127.0.0.1:8765;
    }

    location /screenshots/ {
        proxy_pass http://127.0.0.1:8765;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/sensehub /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

HTTPS（有域名且已完成备案时）：

```bash
sudo certbot --nginx -d 你的域名
```

---

## 6. 验收清单

1. `curl http://127.0.0.1:8765/health` → `{"status":"ok"}`
2. 浏览器打开 `https://你的域名/` → 首页正常
3. 注册：收邮件验证码 → 登录成功
4. `/studio` 发一条消息 → 有 AI 回复
5. admin 登录 → 人员管理可搜用户、发积分

---

## 7. 运维提示

- **更新代码**：`git pull` → `pip install -e .` → `cd web && npm run build` → `sudo systemctl restart sensehub`
- **日志**：`journalctl -u sensehub -f`
- **内存紧张**：确认未安装 ultralytics 权重；`free -h` 观察；必要时升到 4GB
- **域名**：中国大陆公网域名需 **ICP 备案**；仅用 IP 访问可跳过备案但无 HTTPS 品牌感
- **API 费用**：客户对话消耗你的 SiliconFlow/Volcengine 额度，建议设积分门槛或限流

---

## 8. 与本地 Windows 演示的关系

| 环境 | 用途 |
|------|------|
| 阿里云 2C2G | 客户外网体验：注册、浏览、Studio 聊天 |
| 你本机 Windows | 摄像头、语音、Claw 桌面操控、完整多模态 |

两套可共用同一套代码；服务器用本文配置，本地继续用 `scripts/start_backend.ps1` + `start_web.ps1`。

---

## 9. 从 Cursor 一键部署（推荐）

已在仓库准备好脚本，**无需手动逐条敲命令**。

### 购买服务器后

1. 阿里云控制台 → 轻量应用服务器 → 记下 **公网 IP**
2. 防火墙放行 **22、80**（443 有域名再加）
3. 重置/记下 **root 密码**（或绑定 SSH 公钥）

### 本机准备（在 Cursor 终端）

```powershell
cd "I:\SenseHub Agent"

# 填写服务器 IP
copy scripts\deploy\target.env.example scripts\deploy\target.env
# 编辑 target.env：SERVER_HOST、DOMAIN 填公网 IP

# 确认 config\local.env 已配置 API Key、SMTP、JWT_SECRET

# 一键部署（会提示输入 root 密码）
.\scripts\deploy\deploy.ps1
```

脚本会自动：

- 本地 `npm run build` 构建前端（省服务器 2GB 内存）
- 打包上传代码到 `/opt/sensehub`
- 单独上传 `config/local.env`
- SSH 远程安装 Python、Nginx、systemd 并启动

### 部署后访问

`http://你的公网IP/`

### 我能在 Cursor 里帮你远程操作吗？

可以。你把 **公网 IP** 发给我后，我能在 Cursor 终端替你执行 `deploy.ps1`（SSH 密码需你在终端输入，不要贴在聊天里）。

若已配置 SSH 公钥，在 `target.env` 里设置 `SSH_KEY` 路径即可免密部署。

### 更新版本

改完代码后再次运行：

```powershell
.\scripts\deploy\deploy.ps1
```
