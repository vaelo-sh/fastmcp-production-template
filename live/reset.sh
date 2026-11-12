#!/usr/bin/env sh
# Fresh near-empty starting point for the stream: live/start -> live/build (git-ignored).
set -eu
cd "$(dirname "$0")"
rm -rf build
cp -r start build
echo "live/build is ready. Reference solution: live/finished/"
