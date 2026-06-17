# Third-Party Notices

MAAT Web Core uses third-party software, model downloads, and optional data sources.
This file is a practical notice, not legal advice.

The MAAT Web Core source code is licensed under the GNU Affero General Public License v3.0. See `LICENSE`.
Third-party dependencies, model files, browser assets, and optional data downloads keep their own licenses and terms.

MAAT Web Core does not ship model weights or Wikipedia/Kiwix ZIM files. The setup script only offers optional downloads directly from the original hosts.

## Python and JavaScript dependencies

Dependencies installed through `requirements.txt` keep their own licenses. Review the installed package metadata before redistribution or commercial deployment.

Notable runtime components include:

- `llama-cpp-python`
- `PyMuPDF`
- `requests`
- `KaTeX` browser assets

## Optional Gemma 4 GGUF

- Source: `unsloth/gemma-4-26B-A4B-it-GGUF`
- Host: Hugging Face
- Reference: <https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF>
- Model card license indicator: Apache-2.0
- Apache License 2.0 reference: <https://www.apache.org/licenses/LICENSE-2.0>
- Download is opt-in and the files are stored locally under `models/`.
- Check the current model card and upstream terms before redistribution, hosted deployment, or commercial use.

## Optional Wikipedia ZIM

- Source: Kiwix/openZIM Wikipedia ZIM archive
- Host: `download.kiwix.org`
- Download is opt-in and the file is stored locally under `wiki/`.
- Wikimedia text reuse is subject to Wikimedia licensing terms, commonly CC BY-SA 4.0 / GFDL for text, with attribution and share-alike obligations. Media files may use different licenses.
- Wikimedia Terms of Use reference: <https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use>

## KaTeX

MAAT Web Core vendors KaTeX browser assets under `backend/static/vendor/katex/`.

- Project: KaTeX
- License: MIT
- License reference: <https://github.com/KaTeX/KaTeX/blob/main/LICENSE>
- Keep KaTeX license and copyright notices when redistributing the vendored files.

## Generated content

Users are responsible for complying with the applicable licenses and terms of use.
Model outputs, generated code, generated LaTeX/PDF files, summaries, and analyses can be wrong or legally sensitive. Users are responsible for reviewing outputs before publication or redistribution.
