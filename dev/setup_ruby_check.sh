#!/bin/bash
set -euo pipefail
# Check Ruby 3.3 availability for Jekyll documentation

echo "🔍 Checking Ruby 3.3 availability for Jekyll documentation..."
echo ""

RUBY_33_FOUND=false
RUBY_33_PATH=""

# First, check for system Ruby 3.3 (apt, etc.) - avoid mise-managed paths
# Check common system locations first
for POSSIBLE_PATH in /usr/bin/ruby /usr/local/bin/ruby; do
  if [ -x "$POSSIBLE_PATH" ]; then
    RUBY_VERSION=$("$POSSIBLE_PATH" --version 2>&1 | grep -oE "ruby [0-9]+\.[0-9]+" | head -1 | awk '{print $2}')
    if [ -n "$RUBY_VERSION" ] && echo "$RUBY_VERSION" | grep -qE "^3\.3"; then
      RUBY_33_PATH="$POSSIBLE_PATH"
      echo "✅ Ruby 3.3 found via system: $RUBY_33_PATH"
      "$RUBY_33_PATH" --version
      RUBY_33_FOUND=true
      break
    fi
  fi
done

# If not found in system locations, check PATH but exclude mise-managed paths
if [ "$RUBY_33_FOUND" = false ]; then
  RUBY_CMD=$(command -v ruby 2>/dev/null)
  if [ -n "$RUBY_CMD" ] && ! echo "$RUBY_CMD" | grep -qE "(mise|\.mise)"; then
    RUBY_VERSION=$("$RUBY_CMD" --version 2>&1 | grep -oE "ruby [0-9]+\.[0-9]+" | head -1 | awk '{print $2}')
    if [ -n "$RUBY_VERSION" ] && echo "$RUBY_VERSION" | grep -qE "^3\.3"; then
      RUBY_33_PATH="$RUBY_CMD"
      echo "✅ Ruby 3.3 found via system: $RUBY_33_PATH"
      "$RUBY_33_PATH" --version
      RUBY_33_FOUND=true
    fi
  fi
fi

# If not found, check mise
if [ "$RUBY_33_FOUND" = false ]; then
  if command -v mise >/dev/null 2>&1; then
    # Try to find Ruby 3.3 via mise
    MISE_RUBY=$(mise which ruby 2>/dev/null || true)
    if [ -n "$MISE_RUBY" ] && [ -x "$MISE_RUBY" ]; then
      RUBY_VERSION=$("$MISE_RUBY" --version 2>&1 | grep -oE "ruby [0-9]+\.[0-9]+" | head -1 | awk '{print $2}')
      if [ -n "$RUBY_VERSION" ] && echo "$RUBY_VERSION" | grep -qE "^3\.3"; then
        RUBY_33_PATH="$MISE_RUBY"
        echo "✅ Ruby 3.3 found via mise: $RUBY_33_PATH"
        "$RUBY_33_PATH" --version
        RUBY_33_FOUND=true
      fi
    fi
    
    if [ "$RUBY_33_FOUND" = false ]; then
      echo "❌ Ruby 3.3 not found via mise"
      echo ""
      echo "To install Ruby 3.3 via mise:"
      echo "  1. Run: mise install ruby@3.3.0"
      echo ""
      echo "Common installation issues:"
      echo "  - Network issues (check your internet connection)"
      echo "  - mise not in PATH (restart your shell or see docs/contributing.md)"
      exit 1
    fi
  else
    echo "❌ Ruby 3.3 not found and mise is not installed"
    echo ""
    echo "Options:"
    echo "  1. Install via system package manager (Ubuntu/Debian):"
    echo "     sudo apt install ruby3.3 ruby3.3-dev"
    echo ""
    echo "  2. Install via mise (see docs/contributing.md for full setup):"
    echo "     First install mise, then: mise install ruby@3.3.0"
    exit 1
  fi
fi

echo ""
echo "✅ Ruby 3.3 is available! You can use:"
echo "   cd docs && bundle install    # Install Jekyll dependencies"
echo "   cd docs && bundle exec jekyll serve    # Run Jekyll locally"





