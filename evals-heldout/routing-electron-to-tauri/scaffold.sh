#!/usr/bin/env bash
set -euo pipefail

mkdir -p .github/workflows tests

cat > README.md <<'EOF'
# Focus Timer

Focus Timer is a small desktop app built with Electron. It counts down a 25-minute focus session and shows the time left in its window.

Start it with `npm install` and then `npm start`. `npm run dist` builds installers for macOS, Windows and Linux with electron-builder.

Pushing a tag that starts with `v` runs `.github/workflows/release.yml`, which builds the installers on each platform and publishes them to a GitHub release.

The repository checks use only the Python 3 standard library. Its tests run with `python3 -m unittest discover tests`.
EOF

cat > .gitignore <<'EOF'
node_modules/
dist/
EOF

cat > package.json <<'EOF'
{
  "name": "focus-timer",
  "productName": "Focus Timer",
  "version": "1.0.0",
  "description": "A desktop countdown timer for focused work sessions.",
  "private": true,
  "main": "main.js",
  "scripts": {
    "start": "electron .",
    "dist": "electron-builder --publish never"
  },
  "devDependencies": {
    "electron": "31.3.1",
    "electron-builder": "24.13.3"
  },
  "build": {
    "appId": "com.example.focustimer",
    "productName": "Focus Timer",
    "files": ["main.js", "index.html", "renderer.js"],
    "mac": {"target": "dmg"},
    "win": {"target": "nsis"},
    "linux": {"target": "AppImage"}
  }
}
EOF

cat > main.js <<'EOF'
const { app, BrowserWindow } = require("electron");
const path = require("path");

function createWindow() {
  const window = new BrowserWindow({
    width: 360,
    height: 240,
    webPreferences: { contextIsolation: true },
  });
  window.loadFile(path.join(__dirname, "index.html"));
}

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
EOF

cat > index.html <<'EOF'
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'">
    <title>Focus Timer</title>
  </head>
  <body>
    <h1 id="time">25:00</h1>
    <button id="start" type="button">Start</button>
    <button id="reset" type="button">Reset</button>
    <script src="renderer.js"></script>
  </body>
</html>
EOF

cat > renderer.js <<'EOF'
const SESSION_SECONDS = 25 * 60;

let remaining = SESSION_SECONDS;
let ticker = null;

function label(seconds) {
  const minutes = String(Math.floor(seconds / 60)).padStart(2, "0");
  const rest = String(seconds % 60).padStart(2, "0");
  return minutes + ":" + rest;
}

function show() {
  document.getElementById("time").textContent = label(remaining);
}

function tick() {
  remaining = Math.max(0, remaining - 1);
  show();
  if (remaining === 0) {
    clearInterval(ticker);
    ticker = null;
  }
}

document.getElementById("start").addEventListener("click", () => {
  if (ticker === null && remaining > 0) {
    ticker = setInterval(tick, 1000);
  }
});

document.getElementById("reset").addEventListener("click", () => {
  clearInterval(ticker);
  ticker = null;
  remaining = SESSION_SECONDS;
  show();
});

show();
EOF

cat > .github/workflows/release.yml <<'EOF'
name: Release

on:
  push:
    tags:
      - "v*"

jobs:
  installers:
    strategy:
      matrix:
        os: [macos-latest, windows-latest, ubuntu-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm install
      - run: npx electron-builder --publish always
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
EOF

cat > tests/test_package.py <<'EOF'
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def package():
    return json.loads((ROOT / "package.json").read_text(encoding="utf-8"))


class PackageTest(unittest.TestCase):
    def test_package_json_parses_and_names_its_main_script(self):
        self.assertEqual(package()["main"], "main.js")

    def test_every_packaged_file_exists(self):
        for name in package()["build"]["files"]:
            with self.subTest(file=name):
                self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
EOF

git init -q -b main
git config user.name fixture
git config user.email fixture@example.com
git add -A
git commit -q -m "Focus Timer"
