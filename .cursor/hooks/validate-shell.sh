#!/bin/bash
# Read command from stdin
input=$(cat)
command=$(echo "$input" | jq -r '.command')

# Block dangerous commands (Cursor doesn't block these by default!)
dangerous_patterns=(
  "rm -rf /"
  "rm -rf ~"
  "format"
  "mkfs"
  "dd if="
)

for pattern in "${dangerous_patterns[@]}"; do
  if echo "$command" | grep -qi "$pattern"; then
    echo '{"permission": "deny", "user_message": "Dangerous command blocked", "agent_message": "This command is blocked by security policy"}'
    exit 0
  fi
done

# Allow the command
echo '{"permission": "allow"}'
exit 0