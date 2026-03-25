cat > ~/start-n8n.sh << 'EOF'
#!/bin/bash
NODE_FUNCTION_ALLOW_BUILTIN=child_process N8N_RUNNERS_HEARTBEAT_INTERVAL=3600 n8n start
EOF
chmod +x ~/start-n8n.sh