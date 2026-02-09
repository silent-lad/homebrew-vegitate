#!/usr/bin/env bash
#
# release.sh — Tag, push, wait for GitHub, update the Homebrew formula.
#
# Usage:
#   ./scripts/release.sh 0.2.0
#   ./scripts/release.sh          # reads version from __init__.py
#

set -euo pipefail

REPO="silent-lad/homebrew-vegitate"
FORMULA="Formula/vegitate.rb"
INIT_FILE="src/vegitate/__init__.py"

# ── resolve version ──────────────────────────────────────────────

if [[ $# -ge 1 ]]; then
    VERSION="$1"
else
    VERSION=$(grep '__version__' "$INIT_FILE" | head -1 | sed 's/.*"\(.*\)".*/\1/')
fi

TAG="v${VERSION}"

echo ""
echo "  🌿 vegitate release"
echo "  ────────────────────"
echo "  Version : ${VERSION}"
echo "  Tag     : ${TAG}"
echo "  Repo    : ${REPO}"
echo ""

# ── bump __init__.py if version differs ──────────────────────────

CURRENT=$(grep '__version__' "$INIT_FILE" | head -1 | sed 's/.*"\(.*\)".*/\1/')
if [[ "$CURRENT" != "$VERSION" ]]; then
    echo "  → Bumping __init__.py  ${CURRENT} → ${VERSION}"
    sed -i '' "s/__version__ = \".*\"/__version__ = \"${VERSION}\"/" "$INIT_FILE"
    git add "$INIT_FILE"
    git commit -m "Bump version to ${VERSION}"
fi

# ── tag ──────────────────────────────────────────────────────────

if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "  ⚠  Tag ${TAG} already exists locally, skipping tag creation"
else
    echo "  → Creating tag ${TAG}"
    git tag "$TAG"
fi

# ── push ─────────────────────────────────────────────────────────

echo "  → Pushing main + tags to origin"
git push origin main --tags

# ── wait for tarball ─────────────────────────────────────────────

TARBALL_URL="https://github.com/${REPO}/archive/refs/tags/${TAG}.tar.gz"
echo "  → Waiting for GitHub tarball..."
echo "    ${TARBALL_URL}"

MAX_ATTEMPTS=30
ATTEMPT=0
while true; do
    ATTEMPT=$((ATTEMPT + 1))
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -L "$TARBALL_URL")
    if [[ "$HTTP_CODE" == "200" ]]; then
        echo "    ✓ Available (attempt ${ATTEMPT})"
        break
    fi
    if [[ $ATTEMPT -ge $MAX_ATTEMPTS ]]; then
        echo "    ✗ Tarball not available after ${MAX_ATTEMPTS} attempts. Aborting."
        exit 1
    fi
    echo "    … HTTP ${HTTP_CODE}, retrying in 2s (${ATTEMPT}/${MAX_ATTEMPTS})"
    sleep 2
done

# ── compute sha256 ───────────────────────────────────────────────

echo "  → Computing sha256"
SHA256=$(curl -sL "$TARBALL_URL" | shasum -a 256 | awk '{print $1}')
echo "    ${SHA256}"

# ── update formula ───────────────────────────────────────────────

echo "  → Updating ${FORMULA}"

# Update version in url line
sed -i '' "s|archive/refs/tags/v[^\"]*\.tar\.gz|archive/refs/tags/${TAG}.tar.gz|" "$FORMULA"

# Update sha256 line (matches any current value including RELEASE_SHA256)
sed -i '' "s/sha256 \"[^\"]*\"/sha256 \"${SHA256}\"/" "$FORMULA"

# Verify it looks right
echo ""
echo "  ── Updated formula ──"
grep -n 'url\|sha256' "$FORMULA" | head -4 | sed 's/^/    /'
echo ""

# ── commit and push formula ──────────────────────────────────────

git add "$FORMULA"
git commit -m "Update formula to ${TAG} (sha256: ${SHA256:0:12}…)"
git push origin main

echo "  ✓ Done! Users can now run:"
echo ""
echo "    brew update && brew upgrade vegitate"
echo ""
