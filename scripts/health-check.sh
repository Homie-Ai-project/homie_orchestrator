#!/bin/bash

echo "=== Homie Orchestrator Health Check ==="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check Docker
echo "Checking Docker..."
if docker ps >/dev/null 2>&1; then
    print_status 0 "Docker is running"
else
    print_status 1 "Docker is not running"
    echo "Please start Docker and try again."
    exit 1
fi

# Check Docker Compose
echo -e "\nChecking Docker Compose..."
if command -v docker-compose >/dev/null 2>&1; then
    print_status 0 "Docker Compose is available"
else
    print_status 1 "Docker Compose is not available"
fi

# Check containers
echo -e "\nChecking containers..."
CONTAINERS=("postgres" "redis" "orchestrator")
for container in "${CONTAINERS[@]}"; do
    if docker ps --filter "name=$container" --format "table {{.Names}}" | grep -q "$container"; then
        print_status 0 "$container is running"
    else
        print_status 1 "$container is not running"
    fi
done

# Check networks
echo -e "\nChecking networks..."
if docker network ls | grep -q "homie_network"; then
    print_status 0 "homie_network exists"
else
    print_status 1 "homie_network does not exist"
    print_warning "Run: docker network create homie_network"
fi

# Check API
echo -e "\nChecking API..."
if curl -f -s http://localhost:8080/health >/dev/null 2>&1; then
    print_status 0 "API is responding"
    
    # Get API response
    API_RESPONSE=$(curl -s http://localhost:8080/health)
    echo "  Response: $API_RESPONSE"
else
    print_status 1 "API is not responding"
    print_warning "Check orchestrator logs: docker-compose logs orchestrator"
fi

# Check metrics
echo -e "\nChecking metrics..."
if curl -f -s http://localhost:9090/metrics >/dev/null 2>&1; then
    print_status 0 "Metrics endpoint is responding"
else
    print_status 1 "Metrics endpoint is not responding"
fi

# Check database connectivity
echo -e "\nChecking database..."
if docker exec postgres psql -U homie -d homie -c "SELECT 1;" >/dev/null 2>&1; then
    print_status 0 "Database is accessible"
else
    print_status 1 "Database is not accessible"
    print_warning "Check postgres logs: docker-compose logs postgres"
fi

# Check Redis connectivity
echo -e "\nChecking Redis..."
if docker exec redis redis-cli ping >/dev/null 2>&1; then
    print_status 0 "Redis is accessible"
else
    print_status 1 "Redis is not accessible"
    print_warning "Check redis logs: docker-compose logs redis"
fi

# Check disk space
echo -e "\nChecking disk space..."
DISK_USAGE=$(df / | awk 'NR==2{printf "%s", $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    print_status 0 "Disk space is adequate ($DISK_USAGE% used)"
elif [ "$DISK_USAGE" -lt 90 ]; then
    print_warning "Disk space is getting low ($DISK_USAGE% used)"
else
    print_status 1 "Disk space is critically low ($DISK_USAGE% used)"
fi

# Check memory usage
echo -e "\nChecking memory..."
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ "$MEMORY_USAGE" -lt 80 ]; then
    print_status 0 "Memory usage is normal ($MEMORY_USAGE% used)"
elif [ "$MEMORY_USAGE" -lt 90 ]; then
    print_warning "Memory usage is high ($MEMORY_USAGE% used)"
else
    print_status 1 "Memory usage is critically high ($MEMORY_USAGE% used)"
fi

# Check RAUC (if available)
echo -e "\nChecking RAUC..."
if command -v rauc >/dev/null 2>&1; then
    print_status 0 "RAUC is installed"
    
    # Check RAUC status
    if rauc status >/dev/null 2>&1; then
        print_status 0 "RAUC system is functional"
        echo "  $(rauc status --output-format=shell | grep "RAUC_SYSTEM_BOOTED_SLOT")"
    else
        print_warning "RAUC status check failed"
    fi
else
    print_warning "RAUC is not installed (optional for development)"
fi

echo -e "\n=== Health Check Complete ==="

# Summary
echo -e "\nQuick commands:"
echo "  View logs: docker-compose logs -f orchestrator"
echo "  Restart:   docker-compose restart"
echo "  Stop:      docker-compose down"
echo "  Start:     docker-compose up -d"
