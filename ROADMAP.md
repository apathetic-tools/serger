# 🧭 Roadmap

## 🧰 CLI Parameters
Planned command-line flags for future releases:

- `--quiet` / `-q`
- `--verbose` / `-v`
- `--version` / `-v`
- `--config` / `-c`
- `--out` / `-o`
- `--include` and `--exclude`
- `--add-include` and `--add-exclude`
- `--respect-gitignore` and `--no-gitignore`
- `--self-update` — update serger itself  
- `--no-update-check` — skip automatic update check 

## ⚙️ Config File Enhancements

- [ ] Support `.py` configs
- [ ] Ensure all CLI parameters are covered in config
- [ ] Provide a JSON Schema for validation and autocomplete  

## 🧩 Joiner Scripts (Build System)
Exploring bundling options for generating the single-file release:

- [ ] zip file: zipapp / shiv / pyinstaller --onefile

## 🧪 Tests
- [ ] Flesh out tests for additional functionality after it has been added
- [ ] `--selftest` that runs a few minimal checks internally using Python’s `unittest`—so the user can verify that the install works without needing pytest.

## 🧑‍💻 Development 
- [ ] Deploy action when I tag a release should create a release and attach it to the tagged release.

## 💡 Ideas & Experiments
Potential quality-of-life features:

- [ ] Inject version into final bundled script  
- [ ] Implement `--watch` mode for live rebuilds  
- [ ] publish to PyPI, NPM, PACKAGIST, others?

---

> ✨ *ChatGPT was used to help draft language, formatting, and code — plus we just love em dashes.*

<p align="center">
  <sub>😐 <a href="https://apathetic-tools.github.io/">Apathetic Tools</a> © <a href="./LICENSE">MIT-NOAI</a></sub>
</p>
