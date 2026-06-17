# Contributing to MAAT Web Core

Thank you for considering a contribution.

MAAT Web Core is a local-first, modular AI workbench. Contributions should keep that spirit: privacy-aware, inspectable, and friendly to local hardware.

## Ground Rules

- Keep the project local-first by default.
- Do not add cloud calls unless they are explicit, configurable, and documented.
- Do not commit model files, ZIM files, logs, generated outputs, chat histories, memories, or private documents.
- Prefer small, focused changes over large rewrites.
- Keep modules separated. Avoid turning one file into a catch-all system.
- Respect the GNU AGPL v3.0 license.

## Development Setup

```bash
./setup.sh
```

Start the app:

```bash
./start.sh
```

macOS wrappers are available:

```bash
./setup.command
./start.command
```

If the scripts are not executable after downloading or copying the repository:

```bash
chmod +x setup.sh start.sh setup.command start.command
```

If you only want to install dependencies without starting the app:

```bash
MAAT_SETUP_NO_START=1 ./setup.sh
```

## Suggested Workflow

1. Create a feature branch.
2. Make a focused change.
3. Test locally on the smallest reasonable setup.
4. Update documentation if behavior or setup changes.
5. Open a pull request with a clear description.

## Pull Request Checklist

- The app starts locally.
- No private data is included.
- No model weights or large generated files are included.
- New settings have safe defaults.
- New external network behavior is documented and opt-in.
- UI changes are usable on small screens.
- Docs are updated when commands, settings, plugins, or setup steps change.

## Code Style

- Use clear Python and browser-native JavaScript.
- Keep comments useful and short.
- Keep plugin/module boundaries clean.
- Prefer deterministic local behavior over hidden automation.
- Avoid broad exception swallowing unless the user gets a useful log message.

## Plugins

Plugins live in:

```text
plugins/<plugin_name>/plugin.py
```

Useful hooks include:

```python
def on_startup(context): ...
def before_chat(user_input, context): ...
def before_final_response(reply, context): ...
def after_response(reply, context): ...
def after_final_response(reply, context): ...
def command(cmd, context): ...
```

Plugins should not silently exfiltrate prompts, memories, files, or logs.

## Security

Please read [SECURITY.md](SECURITY.md). Do not post exploit details or private data in public issues.

## Legal Notes

MAAT Web Core is licensed under the GNU Affero General Public License v3.0. Third-party dependencies, optional models, and optional Wiki/ZIM files keep their own licenses and terms. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
