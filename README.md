# Serger 🧵 


[![CI](https://github.com/apathetic-tools/serger/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/goldilocks/serger/actions/workflows/ci.yml)
[![License: MIT-a-NOAI](https://img.shields.io/badge/License-MIT--aNOAI-blueviolet.svg)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?logo=discord&logoColor=white)](https://discord.gg/PW6GahZ7)

📘 **[Roadmap](./ROADMAP.md)** · 📝 **[Release Notes](https://github.com/apathetic-tools/serger/releases)**

**Stitch your module into a single file.**
*Because packaging is overrated.*

> [!NOTE]
> Heads up: the AI cooked dinner. It's edible, but watch your step.  
> Detailed bug reports welcome.

## 🚀 Quick Start

The self-contained executable script lives at [**`bin/serger.py`**](./bin/serger.py).  
The only requirement is **Python 3.10+** — no pip, no dependencies.

Download or copy that one file anywhere and run it directly:

```bash
python3 serger.py
```

That’s it. ✨

Everything else in this repo (tests, docs, configs) exists only for developing and maintaining the script itself.

---

## 🧪 Verify Your Install

Serger includes a built-in self-check — no pytest required.  
You can verify that the script works correctly on your system by running:

```bash
python3 serger.py --selftest
```

This creates a tiny temporary project, stiches a few test files, and confirms it completes successfully.  
If you see a ✅ “Self-test passed” message, your installation is working perfectly.

---

### ⚖️ License
- [MIT-a-NOAI License](LICENSE)

You’re free to use, copy, and modify the script under the standard MIT terms.  
The additional rider simply requests that this project not be used to train or fine-tune AI/ML systems until the author deems fair compensation frameworks exist.  
Normal use, packaging, and redistribution for human developers are unaffected.

## 🧩 Run It as a Script

If you prefer a direct executable:

```bash
chmod +x serger.py
./serger.py
```

You can even drop it somewhere on your `PATH` for easy use.

## 💡 Why Python? Other Language Versions?

You don’t need a native build.  
Python 3 ships with most Linux distributions. On Mac, it's one homebrew command away. On Windows, running the script automatically prompts the user to install Python from the Microsoft Store.

Serger is meant to live comfortably next to your other tools — Go, Node.js, Rust, whatever — when all you need is a simple, dependency-free way to copy and package files.

## 🪶 Summary

**Use it. Hack it. Ship it.**
It’s MIT-licensed, minimal, and meant to stay out of your way — just with one polite request: don’t feed it to the AIs (yet).

---

> ✨ *AI was used to help draft language, formatting, and code — plus we just love em dashes.*

<p align="center">
  <sub>😐 <a href="https://apathetic-tools.github.io/">Apathetic Tools</a> © <a href="./LICENSE">MIT-a-NOAI</a></sub>
</p>
