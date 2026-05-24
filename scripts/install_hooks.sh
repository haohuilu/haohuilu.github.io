#!/usr/bin/env bash
# Run once to install the pre-commit hook: bash scripts/install_hooks.sh
set -e
HOOK=".git/hooks/pre-commit"
cat > "$HOOK" << 'EOF'
#!/usr/bin/env bash
# Stamp footer with current month/year on every commit.
MONTH_YEAR=$(date +"%B %Y")
sed -i.bak "s/Updated: [A-Za-z]* [0-9]*/Updated: $MONTH_YEAR/" index.html
rm -f index.html.bak
git add index.html
EOF
chmod +x "$HOOK"
echo "Pre-commit hook installed at $HOOK"
