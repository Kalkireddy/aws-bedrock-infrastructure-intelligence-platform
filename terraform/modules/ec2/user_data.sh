#!/bin/bash
# Update system
yum update -y
yum install -y amazon-cloudwatch-agent

# Configure CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<EOF
{
  "metrics": {
    "namespace": "SREAutomation",
    "metrics_collected": {
      "disk": {
        "measurement": [
          {
            "name": "used_percent",
            "rename": "DiskSpaceUsed",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60,
        "resources": ["*"]
      },
      "mem": {
        "measurement": [
          {
            "name": "mem_used_percent",
            "rename": "MemoryUsed",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60
      }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/messages",
            "log_group_name": "${LOG_GROUP}",
            "log_stream_name": "{instance_id}/messages"
          },
          {
            "file_path": "/var/log/secure",
            "log_group_name": "${LOG_GROUP}",
            "log_stream_name": "{instance_id}/secure"
          }
        ]
      }
    }
  }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Start a sample application that generates logs
cat > /usr/local/bin/sample-app.py <<'PYTHON'
#!/usr/bin/env python3
import time
import random
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

while True:
    operation = random.choice(['read', 'write', 'delete', 'query'])
    user = f"user{random.randint(1, 100)}"
    duration = random.random() * 10
    
    if random.random() > 0.9:
        logger.error(f"ERROR: Database error during {operation} by {user}")
    else:
        logger.info(f"SUCCESS: {operation.upper()} operation by {user} completed in {duration:.2f}s")
    
    time.sleep(random.randint(1, 5))
PYTHON

chmod +x /usr/local/bin/sample-app.py

# Create systemd service for sample app
cat > /etc/systemd/system/sample-app.service <<'SERVICE'
[Unit]
Description=Sample Application
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/sample-app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl enable sample-app
systemctl start sample-app
