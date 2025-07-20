# 🎮 Quick Start Guide

> **From zero to hero in 5 minutes! Your journey to container orchestration mastery starts here.**

## 🚀 The 30-Second Magic Install

**Choose your adventure:**

### 🐧 Linux/macOS (Recommended)
```bash
curl -fsSL https://get.homieos.com/install.sh | bash
```

### 🪟 Windows (PowerShell)
```powershell
iwr -useb https://get.homieos.com/install.ps1 | iex
```

### 🐳 Docker Compose (Any Platform)
```bash
git clone https://github.com/homie/orchestrator.git
cd orchestrator
make quick-start
```

**🎉 That's it! Your orchestrator is running at http://localhost:8080**

---

## 🎯 Your First 5 Minutes

### 1. 👋 Say Hello to Your Orchestrator

Open your browser and visit **http://localhost:8080**

You'll see the beautiful Homie Dashboard with:
- 🟢 **System Status** - All green lights!
- 📊 **Resource Usage** - CPU, Memory, Disk at a glance
- 🐳 **Container Overview** - Your managed services
- 🔔 **Smart Notifications** - System events and alerts

### 2. 🎮 Deploy Your First Service

Click the **"+ Add Service"** button and paste this magic:

```yaml
name: "hello-world"
image: "nginx:alpine"
ports:
  - "8080:80"
volumes:
  - "./data/nginx:/usr/share/nginx/html"
environment:
  WELCOME_MESSAGE: "Hello from Homie Orchestrator!"
labels:
  io.homie.category: "web"
  io.homie.backup: "false"
```

Click **"Deploy"** and watch the magic happen! ✨

### 3. 🌟 See It Live

Visit **http://localhost:8080** to see your service running!

### 4. 📊 Explore the Monitoring

Navigate to the **"Monitoring"** tab to see:
- 📈 **Real-time metrics** for your services
- 🏥 **Health checks** and uptime statistics  
- 🔄 **Resource usage** graphs
- ⚡ **Performance insights**

### 5. 🛡️ Test the Self-Healing

Go to the **"Services"** tab, find your hello-world service, and click **"Stop"**.

Watch as Homie automatically:
1. 🚨 Detects the service is down
2. 🏥 Attempts health recovery
3. 🔄 Restarts the service automatically
4. 🎉 Reports "Service Recovered" notification

**Mind blown? This is just the beginning!** 🚀

---

## 🎯 Level Up: Popular Service Templates

### 🤖 AI Platform Stack (5-Click Deploy!)

```yaml
# File: templates/ai-platform.yaml
services:
  homie_ai:
    image: "homie/ai:latest"
    ports: ["8080:8080", "3000:3000", "11434:11434"]
    volumes: ["./data/homie_ai:/data"]
    environment:
      OLLAMA_BASE_URL: "http://ollama:11434"
    labels:
      io.homie.category: "ai"
      io.homie.backup: "daily"
      
  ollama:
    image: "ollama/ollama:latest"
    ports: ["11434:11434"]
    volumes: ["./data/ollama:/root/.ollama"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    
  nodered:
    image: "nodered/node-red:latest"
    ports: ["1880:1880"]
    volumes: ["./data/nodered:/data"]
    
  mosquitto:
    image: "eclipse-mosquitto:2"
    ports: ["1883:1883"]
    volumes: ["./data/mosquitto:/mosquitto"]
```

**Deploy with:** `homie template deploy smart-home`

### 🔧 Development Environment

```yaml
# File: templates/dev-stack.yaml
services:
  postgres:
    image: "postgres:15"
    environment:
      POSTGRES_DB: "myapp"
      POSTGRES_USER: "dev"
      POSTGRES_PASSWORD: "dev123"
    ports: ["5432:5432"]
    
  redis:
    image: "redis:7-alpine"
    ports: ["6379:6379"]
    
  adminer:
    image: "adminer:latest"
    ports: ["8080:8080"]
    depends_on: ["postgres"]
```

**Deploy with:** `homie template deploy dev-stack`

### 📊 Monitoring & Analytics

```yaml
# File: templates/monitoring.yaml
services:
  grafana:
    image: "grafana/grafana:latest"
    ports: ["3000:3000"]
    volumes: ["./data/grafana:/var/lib/grafana"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: "admin123"
      
  prometheus:
    image: "prom/prometheus:latest"
    ports: ["9090:9090"]
    volumes: ["./config/prometheus:/etc/prometheus"]
```

**Deploy with:** `homie template deploy monitoring`

---

## 🎮 Master the CLI Like a Pro

### Essential Commands

```bash
# Check orchestrator status
homie status

# List all services  
homie services list

# Deploy a service
homie service deploy myapp.yaml

# Scale a service
homie service scale myapp --replicas=3

# View logs (with follow)
homie logs myapp --follow --tail=100

# Backup everything
homie backup create --name="before-update"

# Update the orchestrator
homie self-update

# Get help for any command
homie help service
```

### Power User Shortcuts

```bash
# Quick health check of everything
homie health --all

# Restart all services in a category
homie service restart --category="smart-home"

# Export service configuration
homie service export myapp > myapp-backup.yaml

# Bulk operations
homie service stop --tag="development"
homie service start --tag="development"

# Resource monitoring
homie stats --real-time
```

---

## 🎯 Common Patterns & Pro Tips

### 🔄 Service Dependencies Made Easy

```yaml
services:
  database:
    image: "postgres:15"
    environment:
      POSTGRES_DB: "myapp"
    
  backend:
    image: "myapp/api:latest"
    depends_on: ["database"]  # ⚡ Auto-start order!
    environment:
      DATABASE_URL: "postgresql://postgres:5432/myapp"
    
  frontend:
    image: "myapp/web:latest"
    depends_on: ["backend"]
    ports: ["3000:3000"]
```

### 🛡️ Automatic Backups

```yaml
services:
  important-app:
    image: "myapp:latest"
    volumes: ["./data/app:/data"]
    labels:
      io.homie.backup: "daily"        # 📅 Daily backups
      io.homie.backup.retain: "30"    # 🗂️ Keep 30 days
      io.homie.backup.priority: "high" # 🚨 High priority
```

### 🔥 Hot Reloading for Development

```yaml
services:
  myapp-dev:
    image: "node:18"
    command: "npm run dev"
    volumes:
      - "./src:/app/src"              # 🔄 Live code sync
    environment:
      NODE_ENV: "development"
    labels:
      io.homie.dev: "true"            # 🚀 Development mode
      io.homie.hot-reload: "true"     # ⚡ Auto-restart on changes
```

### 🌍 Environment-Specific Configuration

```yaml
# Base configuration
services:
  myapp:
    image: "myapp:${VERSION:-latest}"
    environment:
      NODE_ENV: "${ENVIRONMENT:-production}"
      API_URL: "${API_URL:-http://localhost:3000}"
      
---
# Override for development
# File: overrides/development.yaml
services:
  myapp:
    volumes:
      - "./src:/app/src"    # 🔧 Source code mounting
    environment:
      DEBUG: "true"
      HOT_RELOAD: "true"
```

**Deploy with environment:** `homie deploy --env=development`

---

## 🎉 Congratulations, You're Now Dangerous! 

You've just learned:
- ✅ **Lightning-fast deployment** of any service
- ✅ **Self-healing infrastructure** that fixes itself
- ✅ **Professional monitoring** without the complexity
- ✅ **Backup strategies** that actually work
- ✅ **Development workflows** that boost productivity

## 🚀 What's Next?

### 🎯 Beginner Level Complete! 
- 📖 **Read the [Architecture Guide](architecture.md)** to understand the magic
- 🏠 **Try the [Smart Home Tutorial](tutorials/smart-home.md)** for real-world usage
- 🔧 **Explore [Advanced Configurations](advanced-config.md)** for power users

### 🚀 Ready for Production?
- 🛡️ **Security Hardening Guide** - Lock down your infrastructure
- 🌍 **Multi-Environment Setup** - Dev, staging, production workflows
- 📊 **Advanced Monitoring** - Custom dashboards and alerting
- 🔄 **CI/CD Integration** - Automated deployments from Git

### 🤝 Join the Community!
- 💬 **Discord Chat** - Get help and share your builds
- 📺 **YouTube Channel** - Video tutorials and live streams  
- 🐛 **GitHub Issues** - Report bugs and request features
- ✍️ **Blog** - Technical deep-dives and case studies

---

## 🆘 Need Help?

**Stuck? We've got you covered!**

### 🔍 Quick Debugging

```bash
# Check orchestrator logs
homie logs orchestrator --tail=50

# Verify system health
homie doctor

# Test connectivity
homie test --all

# Generate debug report
homie debug-report > debug.txt
```

### 🤝 Get Human Help

- 💬 **Discord:** Instant help from the community
- 📧 **Email:** support@homieos.com for technical issues
- 📖 **Docs:** docs.homieos.com for detailed guides
- 🎥 **Video Tutorials:** youtube.com/homie-ai

---

*🎉 Welcome to the Homie family! You're about to build some incredible things.* 🚀
