#!/bin/bash
# ============================================
# CyberRange — Wazuh Agent Deployment (Linux)
# Handles the "mess" of installation & config
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

MANAGER_IP=$1

if [ -z "$MANAGER_IP" ]; then
    # BUG FIX #1: Usage message had wrong script name "wazuh.sh" → corrected to "wazuh_agent.sh"
    echo -e "${YELLOW}Usage: ./wazuh_agent.sh <WAZUH_MANAGER_IP>${NC}"
    exit 1
fi

echo -e "${GREEN}🔄 Started Wazuh Agent Setup...${NC}"

# 1. Install Dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
apt-get update && apt-get install -y curl apt-transport-https lsb-release gnupg2

# 2. Add Wazuh Repository
echo -e "${YELLOW}🔑 Adding GPG Key and Repo...${NC}"
# BUG FIX #2: The original used `gpg --import` which writes a non-dearmored keyring that apt cannot
# read when using `signed-by=`. The key must be dearmored (binary format) via `gpg --dearmor`.
# Changed: curl ... | gpg --import  →  curl ... | gpg --dearmor -o /usr/share/keyrings/wazuh.gpg
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | gpg --dearmor -o /usr/share/keyrings/wazuh.gpg
chmod 644 /usr/share/keyrings/wazuh.gpg
echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" | tee /etc/apt/sources.list.d/wazuh.list

# 3. Install Wazuh Agent
echo -e "${YELLOW}🚀 Installing Wazuh Agent...${NC}"
apt-get update
WAZUH_MANAGER="$MANAGER_IP" apt-get install wazuh-agent -y

# 4. Configure CyberRange Log Monitoring
echo -e "${YELLOW}📝 Configuring log monitoring...${NC}"
OSSEC_CONF="/var/ossec/etc/ossec.conf"

# BUG FIX #3: The XML comment was placed OUTSIDE (before) the <ossec_config> block, producing
# invalid XML that Wazuh cannot parse. Moved the comment inside the block.
#
# BUG FIX #4: The localstack log path referenced the container-internal path
# (/var/lib/localstack/logs/*.log) instead of the HOST-side bind-mount path.
# The docker-compose mounts ./volume → /var/lib/localstack inside the container,
# so on the HOST machine the logs actually live at ./volume/logs/*.log.
# Using an absolute path derived from the project root is more robust; here we use
# /var/lib/localstack/logs/*.log only if the agent is running IN the container, but
# since the agent runs on the HOST, the correct path is the volume mount on the host.
# We resolve it to the CyberRange volume path. Adjust CYBERRANGE_DIR if needed.
CYBERRANGE_DIR="${CYBERRANGE_DIR:-/opt/CyberRange}"

# The agent runs on the HOST, so we must monitor logs that are accessible FROM the host.
# Approach: Use Docker's own container log files at /var/lib/docker/containers/<id>/<id>-json.log
# These are always present on the host regardless of volume mounts, and Wazuh supports
# Docker JSON log format natively.
#
# We resolve container IDs at install time so Wazuh knows exactly which files to watch.
# If containers are recreated, re-run this script to refresh the paths.

get_container_log_path() {
    local container_name="$1"
    local cid
    cid=$(docker inspect --format='{{.Id}}' "$container_name" 2>/dev/null)
    if [ -z "$cid" ]; then
        echo ""  # Container not running — skip
    else
        echo "/var/lib/docker/containers/${cid}/${cid}-json.log"
    fi
}

VULN_APP_LOG=$(get_container_log_path "vulnerable-app")
LOCALSTACK_LOG=$(get_container_log_path "localstack-main")
METADATA_LOG=$(get_container_log_path "metadata-service")

cat <<EOF >> "$OSSEC_CONF"
<ossec_config>
  <!-- CyberRange Custom Log Monitoring -->

  <!-- vulnerable-app: SSRF / CMDi / Info Disclosure events -->
  $([ -n "$VULN_APP_LOG" ] && echo "<localfile>
    <location>${VULN_APP_LOG}</location>
    <log_format>json</log_format>
    <label key=\"container\">vulnerable-app</label>
  </localfile>" || echo "<!-- vulnerable-app not running at install time; start it and re-run -->")

  <!-- localstack: Fake AWS API activity (S3, IAM, Lambda, etc.) -->
  $([ -n "$LOCALSTACK_LOG" ] && echo "<localfile>
    <location>${LOCALSTACK_LOG}</location>
    <log_format>json</log_format>
    <label key=\"container\">localstack</label>
  </localfile>" || echo "<!-- localstack not running at install time; start it and re-run -->")

  <!-- metadata-service: EC2 IMDS requests (credential theft attempts) -->
  $([ -n "$METADATA_LOG" ] && echo "<localfile>
    <location>${METADATA_LOG}</location>
    <log_format>json</log_format>
    <label key=\"container\">metadata-service</label>
  </localfile>" || echo "<!-- metadata-service not running at install time; start it and re-run -->")

  <!-- LocalStack volume logs (structured AWS service logs written to bind-mount) -->
  <localfile>
    <location>${CYBERRANGE_DIR}/volume/logs/*.log</location>
    <log_format>syslog</log_format>
  </localfile>
</ossec_config>
EOF

# 5. Start the Agent
echo -e "${YELLOW}🏁 Starting Wazuh Agent service...${NC}"
systemctl daemon-reload
systemctl enable wazuh-agent
systemctl start wazuh-agent

echo -e "${GREEN}✅ Wazuh Agent is now running and talking to: $MANAGER_IP${NC}"
echo -e "You should see this agent in your Wazuh Dashboard shortly."
