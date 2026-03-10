#!/bin/bash
# ============================================
# CyberRange — Wazuh Manager Deployment (Monitor PC)
# Deploys the full SIEM stack (Manager, Indexer, Dashboard)
# ============================================

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Error: Please run as root (use sudo).${NC}"
  exit 1
fi

echo -e "${GREEN}🔄 Started Wazuh Manager Deployment...${NC}"

# 1. Install Dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
apt-get update && apt-get install -y git curl

# Only install Docker if not already present (avoids conflicts with docker-ce installs)
if ! command -v docker &>/dev/null; then
    echo -e "${YELLOW}🐳 Docker not found — installing...${NC}"
    apt-get install -y docker.io docker-compose
else
    echo -e "${GREEN}🐳 Docker already installed ($(docker --version)) — skipping.${NC}"
    # Install docker-compose standalone if missing
    if ! command -v docker-compose &>/dev/null; then
        apt-get install -y docker-compose
    fi
fi
systemctl enable docker
systemctl start docker

# 2. Clone Wazuh Docker Repository
# BUG FIX #5: Tag "v4.7.2" does not exist in the Wazuh Docker repo.
# Valid release tags follow the pattern v4.X.Y (e.g. v4.7.0, v4.8.0).
# Changed to v4.7.0 which is a real, stable release tag.
if [ ! -d "wazuh-docker" ]; then
    echo -e "${YELLOW}🔑 Cloning Wazuh Docker Repository...${NC}"
    git clone https://github.com/wazuh/wazuh-docker.git -b v4.7.0
fi

# BUG FIX #6: The original `cd` had no error guard. If the clone failed or the
# directory structure differed, subsequent docker compose commands would silently
# run in the wrong directory. Now we `cd` with an explicit failure check.
cd wazuh-docker/single-node || {
    echo -e "${RED}Error: Could not enter wazuh-docker/single-node. Did the clone succeed?${NC}"
    exit 1
}

# 3. Generate Certificates (Required by Wazuh Indexer)
echo -e "${YELLOW}📜 Generating certificates...${NC}"
docker compose -f generate-certs.yml run --rm generator

# 4. Spin up the Manager Stack
echo -e "${YELLOW}🚀 Starting the Wazuh Manager stack...${NC}"
docker compose up -d

# 5. Provide Final Info
IP_ADDR=$(hostname -I | awk '{print $1}')
echo -e "${GREEN}✅ Wazuh Manager is deploying!${NC}"
echo -e "Wait 5-10 minutes for the dashboard to initialize."
echo -e ""
echo -e "Dashboard URL:  https://$IP_ADDR"
echo -e "Username:       admin"
# BUG FIX #7: The password "SecretPassword01!" was never actually set in the Wazuh Docker
# compose configuration, so displaying it would give users the wrong credentials.
# The Wazuh Docker single-node stack ships with the default password "SecretPassword".
# Updated the displayed default password to match the actual Wazuh Docker default.
echo -e "Password:       SecretPassword"
echo -e ""
echo -e "Next, use 'wazuh_agent.sh' on your cloud server with the IP: $IP_ADDR"
