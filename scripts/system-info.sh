#!/bin/bash

echo "=== Homei Orchestrator System Information ==="

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

print_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_section "System Information"
echo "Hostname: $(hostname)"
echo "System: $(uname -a)"
if command -v lsb_release >/dev/null 2>&1; then
    echo "Distribution: $(lsb_release -d 2>/dev/null | cut -f2)"
fi
echo "Uptime: $(uptime -p 2>/dev/null || uptime)"
echo "Current time: $(date)"

print_section "Hardware Information"
echo "Architecture: $(uname -m)"
echo "CPU Info:"
if [ -f /proc/cpuinfo ]; then
    echo "  Model: $(grep "model name" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)"
    echo "  Cores: $(nproc)"
    echo "  CPU MHz: $(grep "cpu MHz" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs 2>/dev/null || echo "N/A")"
fi

echo "Memory:"
if command -v free >/dev/null 2>&1; then
    free -h
fi

echo -e "\nDisk Usage:"
df -h

print_section "Network Information"
echo "Network Interfaces:"
if command -v ip >/dev/null 2>&1; then
    ip addr show | grep -E "(inet |inet6 )" | grep -v "127.0.0.1" | awk '{print "  " $NF ": " $2}'
else
    ifconfig 2>/dev/null | grep -E "(inet |inet6 )" | grep -v "127.0.0.1" | awk '{print "  " $7 ": " $2}'
fi

echo -e "\nListening Ports:"
if command -v ss >/dev/null 2>&1; then
    ss -tulpn | grep LISTEN | grep -E ":(8080|9090|5432|6379)" | awk '{print "  " $1 " " $5}'
else
    netstat -tulpn 2>/dev/null | grep LISTEN | grep -E ":(8080|9090|5432|6379)" | awk '{print "  " $1 " " $4}'
fi

print_section "Docker Information"
if command -v docker >/dev/null 2>&1; then
    echo "Docker version: $(docker --version)"
    echo "Docker info:"
    docker info 2>/dev/null | grep -E "(Server Version|Storage Driver|Logging Driver|Cgroup Driver|Operating System|Architecture)"
    
    echo -e "\nDocker storage:"
    docker system df 2>/dev/null
else
    echo "Docker is not installed"
fi

if command -v docker-compose >/dev/null 2>&1; then
    echo -e "\nDocker Compose version: $(docker-compose --version)"
fi

print_section "Container Status"
if docker ps >/dev/null 2>&1; then
    echo "Running containers:"
    docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
    
    echo -e "\nAll containers:"
    docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.CreatedAt}}"
    
    echo -e "\nDocker images:"
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
else
    echo "Cannot access Docker daemon"
fi

print_section "Docker Networks"
if docker network ls >/dev/null 2>&1; then
    docker network ls
    
    if docker network ls | grep -q "homei_network"; then
        echo -e "\nHomei network details:"
        docker network inspect homei_network --format "{{json .IPAM.Config}}" 2>/dev/null
    fi
fi

print_section "Docker Volumes"
if docker volume ls >/dev/null 2>&1; then
    docker volume ls
fi

print_section "Process Information"
echo "Orchestrator processes:"
ps aux | grep -E "(orchestrator|postgres|redis)" | grep -v grep

echo -e "\nTop processes by CPU:"
ps aux --sort=-%cpu | head -10

echo -e "\nTop processes by Memory:"
ps aux --sort=-%mem | head -10

print_section "System Load"
if [ -f /proc/loadavg ]; then
    echo "Load average: $(cat /proc/loadavg)"
fi

if command -v iostat >/dev/null 2>&1; then
    echo -e "\nDisk I/O:"
    iostat -x 1 1 2>/dev/null | tail -n +4
fi

print_section "Environment Variables"
echo "Orchestrator environment:"
env | grep -E "(ORCHESTRATOR|POSTGRES|REDIS|DOCKER)" | sort

print_section "File System Information"
echo "Data directories:"
for dir in /data /config /backups; do
    if [ -d "$dir" ]; then
        echo "  $dir: $(du -sh "$dir" 2>/dev/null | cut -f1) ($(find "$dir" -type f 2>/dev/null | wc -l) files)"
        ls -la "$dir" 2>/dev/null | head -5
    else
        echo "  $dir: Not found"
    fi
done

print_section "Log Files"
echo "Recent log entries:"
if command -v journalctl >/dev/null 2>&1; then
    echo "System logs (last 5 entries):"
    journalctl -u homei-orchestrator --no-pager -n 5 2>/dev/null || echo "  No systemd service logs found"
fi

echo -e "\nDocker logs (last 5 entries):"
if docker ps --filter "name=orchestrator" --format "{{.Names}}" | grep -q orchestrator; then
    docker logs --tail 5 orchestrator 2>/dev/null || echo "  No orchestrator container logs"
fi

print_section "Security Information"
echo "User information:"
echo "  Current user: $(whoami)"
echo "  User groups: $(groups)"
echo "  Docker group: $(getent group docker 2>/dev/null | cut -d: -f4)"

echo -e "\nFile permissions:"
ls -la /var/run/docker.sock 2>/dev/null
ls -la /opt/homei_orchestrator 2>/dev/null | head -3

print_section "RAUC Information"
if command -v rauc >/dev/null 2>&1; then
    echo "RAUC version: $(rauc --version)"
    echo "RAUC status:"
    rauc status 2>/dev/null || echo "  RAUC status not available"
    
    echo -e "\nRAUC configuration:"
    if [ -f /etc/rauc/system.conf ]; then
        echo "  Configuration file exists: /etc/rauc/system.conf"
        grep -E "(compatible|bootloader)" /etc/rauc/system.conf 2>/dev/null
    else
        echo "  No RAUC configuration found"
    fi
else
    echo "RAUC is not installed"
fi

print_section "Summary"
echo "System Status:"
echo "  Total memory: $(free -h | awk '/^Mem:/ {print $2}')"
echo "  Available memory: $(free -h | awk '/^Mem:/ {print $7}')"
echo "  Disk usage: $(df -h / | awk 'NR==2{print $5}')"
echo "  Load average: $(cat /proc/loadavg 2>/dev/null | awk '{print $1}')"
echo "  Docker containers: $(docker ps --format "{{.Names}}" 2>/dev/null | wc -l) running"

if curl -s http://localhost:8080/health >/dev/null 2>&1; then
    echo -e "  ${GREEN}Orchestrator API: Healthy${NC}"
else
    echo "  Orchestrator API: Not responding"
fi

echo -e "\nGenerated at: $(date)"
echo "Report saved to: system-info-$(date +%Y%m%d-%H%M%S).txt"
