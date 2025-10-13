# SmartDocs AI Backend - Docker Deployment Guide

This guide covers Docker deployment for the SmartDocs AI backend with production-ready configuration, security best practices, and deployment examples.

## Files Created

### 1. Dockerfile
Multi-stage Docker build with security best practices:
- **Base Stage**: Python 3.12-slim with dependencies
- **Production Stage**: Optimized runtime with non-root user
- **Development Stage**: Development tools and auto-reload

### 2. .env.template
Comprehensive environment variable documentation:
- All configuration options with descriptions
- Production vs development considerations
- Security recommendations
- Docker-specific deployment notes

### 3. .dockerignore
Optimized build context exclusions:
- Development files and caches
- Documentation and test files
- Version control and CI/CD files
- Temporary and log files

## Docker Build Commands

### Production Build
```bash
# Build production image
docker build -t smartdocs-ai:latest --target production .

# Build with specific tag
docker build -t smartdocs-ai:v1.0.0 --target production .
```

### Development Build
```bash
# Build development image with tools
docker build -t smartdocs-ai:dev --target development .
```

### Multi-platform Build
```bash
# Build for multiple architectures
docker buildx build --platform linux/amd64,linux/arm64 -t smartdocs-ai:latest --target production .
```

## Environment Configuration

### Required Environment Variables
```bash
# Copy template and configure
cp .env.template .env

# Minimum required configuration
OPENAI_API_KEY=sk-your-openai-api-key-here
ENVIRONMENT=production
```

### Production Environment File (.env)
```bash
# Core Configuration
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000

# AI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.1

# Vector Store
VECTOR_STORE_PROVIDER=chroma
VECTOR_STORE_PERSIST_DIR=/app/backend/vectorstores

# Security
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
CORS_ALLOW_CREDENTIALS=false

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=structured
```

## Deployment Examples

### 1. Basic Docker Run
```bash
# Run with environment file
docker run -d \
  --name smartdocs-ai \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/vectorstores:/app/backend/vectorstores \
  smartdocs-ai:latest
```

### 2. Docker Run with Individual Environment Variables
```bash
docker run -d \
  --name smartdocs-ai \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-your-key-here \
  -e ENVIRONMENT=production \
  -e CORS_ORIGINS=https://yourdomain.com \
  -v smartdocs-vectorstore:/app/backend/vectorstores \
  -v smartdocs-logs:/app/logs \
  --restart unless-stopped \
  smartdocs-ai:latest
```

### 3. Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  smartdocs-ai:
    build:
      context: .
      target: production
    container_name: smartdocs-ai
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ENVIRONMENT=production
      - CORS_ORIGINS=https://yourdomain.com
      - LOG_LEVEL=INFO
      - LOG_FORMAT=structured
    volumes:
      - vectorstore_data:/app/backend/vectorstores
      - app_logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health', timeout=25)"]
      interval: 30s
      timeout: 30s
      retries: 3
      start_period: 5s

volumes:
  vectorstore_data:
  app_logs:
```

### 4. Development Setup
```bash
# Development with live reload
docker run -d \
  --name smartdocs-ai-dev \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-your-key-here \
  -e ENVIRONMENT=development \
  -v $(pwd):/app \
  -v $(pwd)/vectorstores:/app/backend/vectorstores \
  smartdocs-ai:dev
```

## Security Considerations

### Container Security
- ✅ **Non-root user**: Runs as `appuser` (UID 1000)
- ✅ **Minimal base image**: Python 3.12-slim reduces attack surface
- ✅ **Multi-stage build**: Excludes build tools from production image
- ✅ **Health checks**: Built-in health monitoring
- ✅ **Read-only filesystem**: Consider `--read-only` flag with tmpfs mounts

### Environment Security
- ✅ **API key protection**: Never hardcode in Dockerfile
- ✅ **Restricted CORS**: Configure specific origins for production
- ✅ **Structured logging**: JSON format for log aggregation
- ✅ **Volume permissions**: Proper file permissions for data directories

### Network Security
```bash
# Create custom network for isolation
docker network create smartdocs-network

# Run with custom network
docker run -d \
  --name smartdocs-ai \
  --network smartdocs-network \
  -p 8000:8000 \
  smartdocs-ai:latest
```

## Production Deployment Checklist

### Pre-deployment
- [ ] Configure `.env` file with production values
- [ ] Set up persistent volume for vector store data
- [ ] Configure proper CORS origins
- [ ] Set up log aggregation (if using structured logs)
- [ ] Test health check endpoint accessibility

### Deployment
- [ ] Build production image
- [ ] Run container with proper volume mounts
- [ ] Verify health check endpoint (`/health`)
- [ ] Test document upload functionality
- [ ] Test chat/QA functionality
- [ ] Monitor logs for errors

### Post-deployment
- [ ] Set up monitoring and alerting
- [ ] Configure backup for vector store data
- [ ] Implement log rotation
- [ ] Monitor API usage and costs
- [ ] Set up SSL/TLS termination (reverse proxy)

## Volume Management

### Data Persistence
```bash
# Create named volume for data persistence
docker volume create smartdocs-vectorstore
docker volume create smartdocs-logs

# Inspect volume location
docker volume inspect smartdocs-vectorstore
```

### Backup and Restore
```bash
# Backup vector store data
docker run --rm \
  -v smartdocs-vectorstore:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/vectorstore-$(date +%Y%m%d).tar.gz -C /data .

# Restore vector store data
docker run --rm \
  -v smartdocs-vectorstore:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/vectorstore-20241010.tar.gz -C /data
```

## Monitoring and Logging

### Health Monitoring
```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' smartdocs-ai

# Monitor logs
docker logs -f smartdocs-ai

# Access container for debugging
docker exec -it smartdocs-ai /bin/bash
```

### Log Management
```bash
# Configure log rotation
docker run -d \
  --name smartdocs-ai \
  --log-driver json-file \
  --log-opt max-size=100m \
  --log-opt max-file=3 \
  smartdocs-ai:latest
```

## Troubleshooting

### Common Issues

#### 1. OpenAI API Key Not Found
```bash
# Check environment variables in container
docker exec smartdocs-ai env | grep OPENAI

# Verify .env file is properly loaded
docker exec smartdocs-ai python -c "import os; print('Key present:', bool(os.getenv('OPENAI_API_KEY')))"
```

#### 2. Vector Store Permission Issues
```bash
# Fix volume permissions
docker exec -u root smartdocs-ai chown -R appuser:appuser /app/backend/vectorstores
```

#### 3. Health Check Failures
```bash
# Test health endpoint manually
docker exec smartdocs-ai curl -f http://localhost:8000/health || echo "Health check failed"
```

#### 4. CORS Issues
```bash
# Check CORS configuration
docker exec smartdocs-ai python -c "from app.config import get_settings; print('CORS Origins:', get_settings().cors_origins)"
```

## Performance Optimization

### Resource Limits
```bash
# Run with resource limits
docker run -d \
  --name smartdocs-ai \
  --memory=2g \
  --cpus=1.0 \
  -p 8000:8000 \
  smartdocs-ai:latest
```

### Build Optimization
```bash
# Use BuildKit for faster builds
DOCKER_BUILDKIT=1 docker build -t smartdocs-ai:latest .

# Build with specific cache mount
docker buildx build \
  --cache-from type=local,src=/tmp/.buildx-cache \
  --cache-to type=local,dest=/tmp/.buildx-cache \
  -t smartdocs-ai:latest .
```

## Integration Examples

### Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Load Balancer Setup
```yaml
# docker-compose with multiple instances
version: '3.8'

services:
  smartdocs-ai-1:
    build: .
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - vectorstore_data:/app/backend/vectorstores

  smartdocs-ai-2:
    build: .
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - vectorstore_data:/app/backend/vectorstores

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - smartdocs-ai-1
      - smartdocs-ai-2

volumes:
  vectorstore_data:
```

This deployment guide ensures secure, scalable, and maintainable Docker deployments of the SmartDocs AI backend.