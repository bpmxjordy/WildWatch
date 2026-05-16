# Deploying WildWatch Agent on Oracle Cloud Free Tier

## Prerequisites

- Oracle Cloud free tier instance (ARM Ampere A1 recommended: 2+ OCPUs, 6+ GB RAM)
- Ubuntu 22.04 or later (aarch64)
- SSH access to the instance

## 1. Server Setup

SSH into your Oracle instance and install Docker:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt install -y docker-compose-plugin

# Log out and back in for group to take effect
exit
```

## 2. Clone & Configure

```bash
git clone https://github.com/bpmxjordy/WildWatch.git
cd WildWatch/agent

# Create environment file
cat > .env << 'EOF'
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key

# Optional tuning
FRAME_INTERVAL_SECONDS=60
MAX_CONCURRENT_EXTRACTIONS=4
BATCH_SIZE=5
EOF
```

## 3. Build & Run

```bash
# Build the image (first build takes ~5-10 min on ARM)
docker compose build

# Start in background
docker compose up -d

# View logs
docker compose logs -f wildwatch-agent
```

The SpeciesNet model (~420MB) downloads on first run. Subsequent restarts use the cached model from the Docker volume.

## 4. Management Commands

```bash
# Stop the agent
docker compose down

# Restart after code changes
docker compose build && docker compose up -d

# View resource usage
docker stats wildwatch-agent

# Clear model cache (forces re-download)
docker volume rm agent_model-cache
```

## 5. Auto-Update (Optional)

Create a cron job to pull and rebuild nightly:

```bash
crontab -e
```

Add:
```
0 3 * * * cd /home/ubuntu/WildWatch/agent && git pull && docker compose build --quiet && docker compose up -d
```

## 6. Oracle Cloud Firewall

No inbound ports needed — the agent only makes outbound connections to:
- YouTube (frame extraction)
- Supabase (API + storage uploads)

## Resource Estimates

| Instance Size | Streams | Interval | Notes |
|---|---|---|---|
| 1 OCPU / 6GB | ~20 streams | 90s | Tight on RAM during inference |
| 2 OCPU / 12GB | ~40 streams | 60s | Recommended for full stream list |
| 4 OCPU / 24GB | ~40 streams | 30s | Fastest processing |

## Troubleshooting

**Out of memory**: Reduce `BATCH_SIZE` to 2-3 or increase `FRAME_INTERVAL_SECONDS` to 90+.

**yt-dlp errors**: YouTube occasionally rate-limits. The agent handles this gracefully with retries.

**Model download fails**: Check outbound internet access. Oracle free tier sometimes needs a NAT gateway for egress.
