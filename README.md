<p align="center">
  <img src="backend/static/maat-core.svg" alt="MAAT Web Core Logo" width="160">
</p>

# MAAT Web Core

MAAT Web Core ist ein lokaler, modularer KI-Web-Core mit Fokus auf langfristiges Memory, Projektkontext, Offline-Wissen, lokale GGUF-Modelle und MAAT-basierte Selbstregulation.

Es kombiniert Chat, Modellsteuerung, Langzeitgedächtnis, Offline-Wiki, Projektgedächtnis, Dokument-/Code-Erzeugung, Feedback-Learning und Antwortdiagnose in einer gemeinsamen Weboberfläche.

Lizenz: GNU Affero General Public License v3.0. Siehe [LICENSE](LICENSE).

Projektseite: [www.maat-research.com](https://www.maat-research.com)

Mitmachen und Sicherheit: [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md)

> **Hinweis:** MAAT Web Core ist eine frühe öffentliche Version und wird aktiv weiterentwickelt. Es können noch Fehler, unvollständige Funktionen und Modell-/Plattform-Unterschiede auftreten. Bugfixes, Tests und Verbesserungen werden schrittweise ergänzt.

## Highlights

- **Local-first:** Läuft lokal mit GGUF-Modellen über `llama-cpp-python` oder optional über lokale OpenAI-kompatible APIs.
- **Langzeitgedächtnis:** Super Memory, Person Graph, Timeline, Archiv und gewichtete Lessons.
- **Projektwissen:** Project Memory für Forschungsprojekte, Formeln, Paper, Trigger und Kontext.
- **Offline-Wissen:** Optionaler Kiwix/ZIM-Reader mit klar gekennzeichnetem Offline-Wiki-Kontext.
- **MAAT-Diagnose:** H/B/S/V/R, Stability, CCI, Balance, Claim Guard, Anti-Hallu und Reflection.
- **Werkzeugschicht:** Code/LaTeX/HTML-Dateien erzeugen, Python ausführen, LaTeX zu PDF kompilieren und Fehler an die KI zurückgeben.
- **Transparenz:** Log-Ansicht, Debug-Blöcke, sichtbare Quellenhinweise und aufklappbares Thinking-Fenster.

## Why MAAT Web Core?

Viele lokale KI-Tools sind sehr stark in einem bestimmten Bereich: Modell-Laden, Chat-UI, Rollen-/Charakter-Workflows oder API-Anbindung. MAAT Web Core konzentriert sich auf einen anderen Schwerpunkt: langfristiges, nachvollziehbares Arbeiten mit einer lokalen KI.

Der Fokus liegt auf:

- **Kontext statt nur Chatverlauf:** Memory, Projektwissen, Offline-Wiki und Chat-Suche arbeiten als getrennte Quellen.
- **Lernen aus Feedback:** Lessons speichern Denkregeln, nicht nur Ereignisse.
- **Quellenbewusstsein:** Memory, Wiki und Projektkontext sollen für das Modell unterscheidbar bleiben.
- **Arbeitsfähigkeit:** Die KI kann Dateien erzeugen, Code prüfen, Python ausführen und LaTeX/PDF-Workflows begleiten.
- **Selbstregulation:** MAAT-Module prüfen Antworten auf Klarheit, Balance, Evidenz, Kontextbezug und Halluzinationsrisiko.

Kurz gesagt: MAAT Web Core ist weniger ein reines Chat-Frontend und mehr eine lokale KI-Arbeitsumgebung für längere Projekte, Forschung, Dokumentation und iteratives Denken.

## Was ist MAAT Web Core?

MAAT Web Core ist kein Cloud-Dienst und kein reiner Chat-Wrapper. Es ist ein lokaler Forschungs- und Arbeitskern, der ein Sprachmodell mit zusätzlichen Kontext- und Kontrollschichten verbindet.

Die Grundidee:

- Das Modell erzeugt die Antwort.
- MAAT-Module bereiten Kontext vor, prüfen Behauptungen, strukturieren Stil und erkennen Risiken.
- Memory-Module speichern wichtige Ereignisse, Beziehungen, Projekte und Lessons.
- Tool-Module erzeugen Dateien, kompilieren LaTeX, führen Python aus und liefern Fehlerfeedback zurück.
- Debug- und Log-Ansichten machen sichtbar, welche Quellen und Module gerade aktiv waren.

MAAT steht dabei für fünf Diagnosefelder:

- `H` Harmonie: Klarheit, Kohärenz und Struktur
- `B` Balance: Abwägung, Gegenperspektive und Vermeidung blinder Zustimmung
- `S` Schöpfungskraft: nützliche Ideen, Beispiele und kreative Verbindungen
- `V` Verbundenheit: Bezug zu User, Verlauf, Projekt und Kontext
- `R` Respekt: Ehrlichkeit, Unsicherheit markieren, keine unbelegten Behauptungen

Diese Felder sind keine zwingende Philosophie für Nutzerinnen und Nutzer. Im Web Core dienen sie praktisch als Bewertungs-, Debug- und Prompting-Schicht.

## Funktionsüberblick

- **Lokaler Chat:** Weboberfläche mit Streaming, Chatliste, Copy, Vorlesen, Thinking-Fenster und Anhängen.
- **Direkter GGUF-Loader:** Lädt Modelle über `llama-cpp-python`, inklusive Systemscan für Threads/GPU-Layers. Ausgelegt für moderne GGUF-Modelle wie Qwen 3.6 und Google Gemma 4.
- **OpenAI-kompatibler Adapter:** Optionaler Betrieb gegen lokale `/v1/chat/completions`-APIs, z.B. llama.cpp server oder andere lokale OpenAI-kompatible Backends.
- **Super Memory:** Arbeits-, episodisches, semantisches und keyword-basiertes Gedächtnis mit User-Auswahl.
- **Person Graph:** Strukturierte Beziehungen zwischen Usern und erwähnten Personen, inklusive Confidence und Status.
- **Project Memory:** Projektwissen, Formeln, Paper, Trigger und Projektkontext getrennt von persönlichen Memories.
- **Offline Wiki:** Optionaler Kiwix/ZIM-Kontext mit Quellenhinweis im Prompt.
- **Chat Search:** Durchsuchbares Archiv alter Chatlogs per SQLite/FTS.
- **Context Optimizer:** Begrenzt und priorisiert Kontext, damit lokale Modelle nicht unnötig aufgeblasen werden.
- **Chat Compressor:** Verdichtet alte Turns, entfernt Thinking und kann Chat-Titel automatisch setzen.
- **MAAT Diagnostics:** H/B/S/V/R, Stability, CCI, Balance, Claim Guard, Anti-Hallu, Reflection und Rewrite.
- **Adaptive Learning:** Speichert Lessons mit Confidence statt nur Ereignisse.
- **Docs/File Builder:** Erkennt Code-/LaTeX-/HTML-Blöcke, speichert Dateien, kompiliert PDFs und kann Python ausführen.
- **Plugin-System:** Kleine Erweiterungen können Hooks und Commands registrieren.

## Voraussetzungen

MAAT Web Core braucht eine lokale Python-Installation.

Empfohlen:

- Python 3.10 oder neuer
- Python 3.11 empfohlen
- `python3` und `python3 -m venv` müssen im Terminal verfügbar sein

Prüfen:

```bash
python3 --version
python3 -m venv --help
```

Falls Python fehlt:

- macOS: Python von [python.org](https://www.python.org/downloads/) installieren oder per Homebrew: `brew install python`
- Debian/Ubuntu: `sudo apt install python3 python3-venv curl`
- Andere Linux-Distributionen: Python 3 und das jeweilige `venv`-Paket über den Paketmanager installieren

## Kurzstart

Einmaliges Setup:

```bash
./setup.sh
```

Auf macOS geht auch:

```bash
./setup.command
```

Falls macOS nach einem ZIP-Download oder Kopieren von einem USB-Laufwerk meldet, dass die Dateien nicht ausführbar sind:

```bash
chmod +x setup.sh start.sh setup.command start.command
```

Danach erneut starten:

```bash
./setup.command
```

Das Setup installiert die Python-Abhängigkeiten in `.venv`, prüft den RAM und fragt optional, ob ein empfohlenes Gemma-4-GGUF-Modell und/oder die deutsche Offline-Wikipedia-ZIM geladen werden soll. GGUF-Modelle werden dabei über `huggingface_hub` geladen; die ZIM-Datei kommt direkt von Kiwix.

Für den direkten GGUF-Loader fragt das Setup außerdem, ob `llama-cpp-python` installiert werden soll. Standard ist Apple Silicon mit Metal, sonst ein CPU-sicherer Build. Manuell steuerbar:

```bash
MAAT_LLAMA_CPP_BUILD=cpu ./setup.sh
MAAT_LLAMA_CPP_BUILD=metal ./setup.sh
MAAT_LLAMA_CPP_BUILD=cuda ./setup.sh
MAAT_LLAMA_CPP_BUILD=vulkan ./setup.sh
```

Nach erfolgreichem Setup startet `setup.sh` automatisch `start.sh`. Wenn du nur installieren willst:

```bash
MAAT_SETUP_NO_START=1 ./setup.sh
```

Linux-Hinweis:

```bash
sudo apt install python3 python3-venv curl
./setup.sh
./start.sh
```

Für Vorlesen unter Linux nutzt MAAT Web Core automatisch `spd-say`, `espeak-ng` oder `espeak`, falls installiert. Beispiel:

```bash
sudo apt install speech-dispatcher espeak-ng
```

Für `.tex -> .pdf` im Docs/File-Builder wird zusätzlich `pdflatex` benötigt. Das Setup prüft das und kann auf Debian/Ubuntu optional Basispakete installieren:

```bash
sudo apt install texlive-latex-base texlive-latex-recommended texlive-fonts-recommended
```

Für größere Paper:

```bash
sudo apt install texlive-latex-extra
```

Falls `apt update` mit Signatur-, Schlüssel- oder Repository-Fehlern abbricht, liegt das meist nicht an MAAT Web Core, sondern an der lokalen Paketquellen-Konfiguration.

Dann zuerst die APT-Quellen prüfen und reparieren:

```bash
sudo apt update
```

Danach LaTeX erneut installieren. Bitte keine fremden Repository-Schlüssel blind importieren, sondern die Paketquellen passend zur eigenen Distribution korrigieren.

Auf macOS empfiehlt sich MacTeX/BasicTeX, wird aber wegen der Größe nicht automatisch installiert.

RAM-Auswahl im Setup:

```text
unter 24 GB  -> Gemma 4 Q2, ctx 20k
ab 24 GB    -> Gemma 4 Q3, ctx 40k
ab 32 GB    -> Gemma 4 Q4, ctx 40k
```

Manueller Start:

```bash
cd maat-web-core
python3 run.py
```

Dann im Browser öffnen:

```text
http://127.0.0.1:8787
```

Alternativ mit Startscript:

```bash
./start.sh
```

Auf macOS per Doppelklick/Terminal:

```bash
./start.command
```

Das Startscript kann interaktiv Benutzername und Passwort abfragen.

Hinweis zu optionalen Downloads: Modelle und ZIM-Dateien werden nicht mit diesem Repository ausgeliefert. Das Setup lädt sie nur nach Zustimmung direkt von Hugging Face bzw. Kiwix und schreibt die lokalen Pfade in `data/settings.json`. Siehe auch [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Grundidee

MAAT Web Core trennt die KI in mehrere klare Schichten:

```text
User Input
  -> Reality / User / Style / Emotion
  -> Offline Wiki / Super Memory / Project Memory
  -> Context Optimizer / Compressor
  -> Claim Guard / Balance / Thinking / Reflection
  -> lokales Modell
  -> Rewrite / Anti-Hallu / Feedback / Memory Save / File Builder
  -> Chat UI
```

Ziel ist nicht nur Chatten, sondern ein lokaler Forschungs- und Arbeitskern:

- Ereignisse werden im Super Memory gespeichert.
- Denkregeln werden als Lessons gespeichert.
- Projekte, Formeln und Papers werden separat verwaltet.
- Offline-Wiki und Memory werden als Quellen gekennzeichnet.
- Antworten werden nach H/B/S/V/R analysiert.
- Der Dialog bleibt lokal und modular erweiterbar.

## Passwortschutz

`start.command` fragt beim Start:

```text
Passwortschutz aktivieren? [J/n]:
Benutzer [admin]:
Passwort [Enter = Standard]:
```

Per Environment:

```bash
export MAAT_WEB_AUTH_ENABLED="1"
export MAAT_WEB_AUTH_USER="admin"
export MAAT_WEB_AUTH_PASSWORD="maat"
python3 run.py
```

Ohne Passwort:

```bash
export MAAT_WEB_AUTH_ENABLED="0"
python3 run.py
```

Wichtig: Wenn der Web Core im LAN erreichbar ist, sollte Basic Auth aktiv sein.

## Oberfläche

### Chat

Der Chat ist die Hauptansicht:

- mittiger Chatverlauf
- Seitenleiste mit Chatverlauf, Vorschau, Datum und Nachrichtenzahl
- Chat umbenennen und löschen
- Copy-Button pro Nachricht
- Vorlesen per macOS `say`, Linux `spd-say`/`espeak-ng`/`espeak` oder Browser-Fallback, mit Stop beim zweiten Klick
- Thinking ein-/ausklappbar, auch während Streaming
- Modellfavoriten direkt im Chat auswählbar
- Benutzer-Dropdown für Multi-User-Memory
- Anhänge für große Texte aus Paste/Upload

### Log

Die Log-Ansicht zeigt strukturierte Runtime-Ereignisse:

- Modell-/Adapterdetails
- Prompt-Token-Schätzung
- Prompt Processing / erstes Token
- SuperMemory Recall
- Offline-Wiki Treffer
- Context Optimizer Report
- Compressor Report
- Project Memory Treffer
- Claim Guard / Balance / Feedback Debug

### Help

Der Help-Tab kommt direkt vom aktiven CommandRouter und zeigt:

- verfügbare Commands
- MAAT-Kurzbefehle
- geladene Plugins

### Projekte

Der Projekt-Tab verwaltet MAAT-Projekte:

- Projekt anlegen und öffnen
- Tags und Trigger
- Kontext und Beschreibung
- Formeln
- Papers
- Projekt-Einträge wie Erkenntnis, Experiment, Entscheidung
- automatischer Recall in den Prompt

### Docs

Der Docs/File-Builder verwaltet erzeugte Dateien:

- Python-Dateien speichern
- Python ausführen
- Python-Fehler an die KI zurückmelden
- LaTeX speichern
- LaTeX zu PDF kompilieren
- HTML speichern/öffnen
- Downloads anbieten
- Dokumente aus der UI löschen

## Modell-Anbindung

### OpenAI-kompatible API

Beispiel fuer einen lokalen OpenAI-kompatiblen Server:

```text
http://127.0.0.1:8080/v1
```

Der Adapter ist mit lokalen OpenAI-kompatiblen Backends nutzbar, z.B. llama.cpp server oder andere lokale Tools, die `/v1/chat/completions` anbieten.

Falls ein anderes lokales Backend einen anderen Port nutzt, trage dessen `/v1`-Basis-URL in den Settings ein, z.B.:

```text
http://127.0.0.1:<port>/v1
```

### Direkter llama.cpp GGUF Loader

Der Adapter `llama_cpp_direct` lädt GGUF direkt im Web-Core-Prozess über `llama-cpp-python`.

Voraussetzung:

```bash
python3 -m pip install llama-cpp-python
```

Das Setup fragt diese Installation automatisch ab. Für manuelle Builds:

```bash
# Apple Silicon / Metal
CMAKE_ARGS="-DGGML_METAL=on" FORCE_CMAKE=1 python3 -m pip install --upgrade --force-reinstall --no-cache-dir llama-cpp-python

# Linux CPU-safe
python3 -m pip install --upgrade llama-cpp-python

# Linux NVIDIA/CUDA, nur wenn CUDA Toolkit vorhanden ist
CMAKE_ARGS="-DGGML_CUDA=on" FORCE_CMAKE=1 python3 -m pip install --upgrade --force-reinstall --no-cache-dir llama-cpp-python
```

Im UI:

```text
Adapter: llama.cpp direkt (GGUF)
GGUF-Modellpfad: absoluter Pfad zur .gguf
CTX: Kontextgröße
Threads: CPU-Threads
GPU Layers: Offload-Layer, bei Metal-Build oft hoch setzen
```

Das Modell wird lazy geladen: erst bei der ersten Anfrage. Danach bleibt es im RAM-Cache. Beim Modellwechsel wird der Cache geleert.

### Systemscan / Auto-Loader

Unter Settings kann der Systemscan Threads und GPU-Layers automatisch setzen.

- macOS Apple Silicon: Metal-Offload wird bevorzugt.
- macOS Intel: CPU-Modus wird konservativ gesetzt.
- Linux NVIDIA: GPU-Offload wird vorgeschlagen, wenn `llama-cpp-python` mit CUDA/Vulkan gebaut ist.
- Linux AMD/Intel/DRM: sichere CPU-Werte; Vulkan/ROCm kann später manuell getestet werden.
- 16-GB-Klasse: konservativer CTX-Hinweis für Q2/kleinere Kontexte.

CTX bleibt absichtlich immer separat manuell einstellbar, auch im Auto-Modus.

### Modellordner und Favoriten

Standard-Suchpfade:

```text
./models
../models
```

Weitere Suchpfade:

```bash
MAAT_WEB_GGUF_DIRS="/pfad/zu/models:/zweiter/pfad" python3 run.py
```

In den Settings kann ein beliebiger Modellordner gesetzt werden. Angekreuzte Favoriten erscheinen direkt im Chatfenster.

### Systemscan

Der Systemscan kann sinnvolle Loaderwerte vorschlagen:

- Threads
- GPU-Layers
- Loader-Modus
- Speicherorientierte Empfehlungen

Der CTX-Wert bleibt absichtlich separat einstellbar, auch wenn Auto-Modus aktiv ist.

### Restart aus der UI

Im Settings-Tab gibt es einen `Restart`-Button. Er ruft lokal `/api/restart` auf, speichert vorher die aktuellen Settings und ersetzt dann den laufenden Python-Prozess mit denselben Startargumenten. Die Oberfläche wartet kurz auf `/api/state` und lädt sich automatisch neu, sobald der Web Core wieder erreichbar ist.

### Qwen 3.6 / Google Gemma 4 / LFM

Der direkte GGUF-Adapter erkennt grob per Dateiname:

- `qwen`, inklusive Qwen 3.x / Qwen 3.6 GGUF-Varianten
- `gemma`, inklusive Google Gemma 4 GGUF-Varianten
- `lfm` / `liquid`

MAAT Web Core ist besonders auf Qwen- und Gemma-Workflows vorbereitet:

- Qwen: `/think` und `/no_think` werden für modellnahes Thinking genutzt.
- Google Gemma 4: Thinking wird über Prompt-/Systeminstruktionen gesteuert, weil Gemma kein Qwen-kompatibles `/think`-Tokenprotokoll nutzt.
- Gemma/LFM: Flash-Attention und Batch-/uBatch-Werte werden konservativer behandelt. Bei Decode-Fehlern kann der Adapter mit kleinerem Kontext erneut versuchen.

Hinweis: Kompatibilität hängt immer von konkreter GGUF-Datei, Quantisierung, `llama-cpp-python`-Build, RAM und Kontextgröße ab.

## Thinking

Es gibt zwei Ebenen:

### Modell-Thinking

Der Schalter `Think an/aus` steuert modellnahes Thinking.

- Bei Qwen wird `/think` oder `/no_think` in den User-Turn eingefügt.
- Bei Thinking aus werden sichtbare Denkspuren gefiltert.
- Bei Thinking an werden Denkspuren in einem aufklappbaren Thinking-Fenster gesammelt.

### MAAT Thinking

Der MAAT-Regler `0-100%` steuert zusätzliche stille Antwortverbesserung:

- `0%`: aus
- `50%`: mittlere Qualitätsprüfung
- `100%`: starke H/B/S/V/R-Prüfung mit Repair-Hinweisen

MAAT Thinking ist nicht dasselbe wie Chain-of-Thought. Es injiziert Qualitätsregeln, aber soll keine internen MAAT-Tags sichtbar ausgeben.

## Context Management

### Chat Compressor

Der Chat Compressor verdichtet ältere Turns prompt-seitig:

- lässt die letzten Turns roh
- erstellt eine lokale Zusammenfassung
- kann Chat-Titel automatisch setzen
- kann Summary als Chat-Metadaten speichern
- entfernt Thinking und interne Tags aus der Zusammenfassung

Settings:

- Trigger-Turns
- rohe Turns behalten
- Kontext-Schwelle
- Summary-Zeichen
- Debug

### Context Optimizer

Der Context Optimizer sitzt kurz vor dem finalen Prompt:

- injiziert einen stillen aktuellen-User-Block
- priorisiert den aktuellen User gegenüber altem Verlauf
- trennt Quellen: Super Memory, Offline Wiki, Project Memory, Lessons
- begrenzt Memory-Kontext auf ein Budget
- berechnet eine Kontextqualität nach H/B/S/V/R
- Debug zeigt Memory vorher/nachher, Quellen und Stability

Standard:

```text
max memory items: 6
max memory chars: 2600
```

## MAAT Module

### MAAT Value Core

Grundregeln für H/B/S/V/R:

- H: Klarheit und Kohärenz
- B: Balance, keine blinde Zustimmung
- S: Ideen und nützliche Verbindungen
- V: Bezug zu User und Kontext
- R: Ehrlichkeit, keine Halluzination

Modi:

- `light`
- `standard`
- `strict`

### MAAT Engine

Analysiert finale Antworten heuristisch:

- H
- B
- S
- V
- R
- Stability
- Maat Value
- Fokusfelder

Optional kann der Debugblock vor der Antwort angezeigt werden.

### Advanced CCI

Berechnet einen zusätzlichen Kritikalitätswert:

- ordered
- productive / critical
- chaotic / instability risk

Der CCI ist eine Diagnose, kein Qualitätsranking.

### MAAT Balance

Regelt Balance:

- Agreement-Pressure-Erkennung
- Gegenperspektive bei starken/absoluten Aussagen
- Kontextgewichtung
- B_dynamic
- optional Self-Reflection

### Claim Guard

Schützt gegen überstarke Behauptungen:

- wissenschaftlich bewiesen
- perfekt
- garantiert
- besser/schlechter-Vergleiche
- Selbstlob
- riskante Faktenaussagen

Kann vor der Antwort warnen und nach der Antwort einen Output-Repair anwenden.

### PLP Anti-Hallu

Prüft Antworten auf Halluzinationsrisiko:

- Unsicherheit markieren
- fehlende Evidenz erkennen
- Fakt/Symbolik trennen
- bei Symbolik und Gematria nicht blockieren, sondern klar einordnen

### Reflection

Merkt den letzten stabilen Reflexionszustand und kann eine Prompt-Regel injizieren, damit Score-Ausgaben nicht doppelt oder chaotisch formatiert werden.

### Rewrite Loop

Räumt finale Antworten leicht auf:

- kurze Repair-Schicht
- optionales Kürzen
- Schutz vor zu schwachen H/B/S/V/R-Feldern

Für Code/LaTeX ist Vorsicht wichtig: Der Rewrite darf Codeblöcke nicht beschädigen.

### Style

Steuert Ausgabeformat:

- Intent-Erkennung
- Greeting Override
- Ton: neutral, friendly, enthusiastic, scientific, mentor, philosophical
- automatische Tonerkennung
- Anrede-Modus
- Absatzdichte
- Überschriften
- Listen
- Emoji-Regler
- Old-School-Smiley-Regler

### Emotion

Erkennt emotionale Eingaben und steuert Nähe:

- detect
- simulate
- full

R bleibt harte Grenze: Die KI darf keine echten Gefühle vortäuschen.

### Identity

Injiziert das Selbstbild der MAAT-KI:

- Name
- Modus: balanced, warm, deep, symbolic
- optional nur einmal pro Chat

### Reality Layer

Injiziert Live-Datum/Uhrzeit:

- `/maat time`
- `/maat date`
- Reality Preview

Live-Kontext wird von Memory getrennt.

### Spirit

Optionaler MAAT-Spirit-Block:

- MAAT-Sprache
- Formeln
- Reflexionshaltung
- kompakt/standard/full

Kann einmalig pro Chat injiziert werden, um Kontext zu sparen.

## Super Memory

Super Memory ist das Langzeitgedächtnis:

- Working Memory
- Episodic Memory
- Semantic Memory
- Keyword-Saves
- Archiv
- Dreaming
- Person Recall
- Person Graph

### Saves

Die KI kann am Ende einer Antwort einen Save schreiben:

```text
save: (memory=..., keywords=..., tags=..., always=false, type=fact, field=V, priority=normal)
```

Im Chat erscheint daraus eine aufklappbare Save-Box.

Saves aus Thinking werden ignoriert. Nur Saves aus dem finalen sichtbaren Chat-Ergebnis sollen gespeichert werden.

### User-Auswahl

Der aktuelle User wird im UI gewählt. Dieser Wert ist maßgeblich:

- erwähnte Namen sind nicht automatisch Autoren
- neue User-Aussagen werden dem aktiven User zugeordnet
- user-spezifische Memories werden bevorzugt

### Person Graph

Der Person Graph speichert Beziehungen:

- Source User
- Zielperson
- Beziehung
- Emotion
- MAAT-Feld
- Status: inferred / confirmed
- Maturity: NEW / PROMISING / ESTABLISHED / CORE
- Stärke, Confidence, Evidenz

Im MAAT-Tab kann der Graph bearbeitet werden.

### Timeline / Archiv

Zeitfragen werden unterstützt:

- gestern
- vorgestern
- vor 10 Tagen
- vor 3 Wochen
- vor 3 Monaten
- vor 100 Tagen
- am 15.05.2026

Wenn ein exaktes Datum leer ist, bekommt die KI einen Kontext über den Fehltreffer und ggf. nahe Erinnerungen.

Alte Memories können archiviert und über Archiv/Dreaming weiter gefunden werden.

## Adaptive Learning

Adaptive Learning speichert Denkregeln statt Ereignisse.

Memory:

```text
Was passiert ist.
```

Lessons:

```text
Wie die KI künftig besser antworten soll.
```

Lesson-Felder:

- id
- timestamp
- source
- category
- type
- lesson
- success_count
- fail_count
- score
- confidence
- effective_score
- last_used

Confidence:

```text
(success_count + 1) / (success_count + fail_count + 2)
```

Maximal zwei passende Lessons werden pro Antwort injiziert. Auswahl ist gewichtet, nicht immer identisch.

## Feedback Tool

Das Feedback Tool analysiert die letzte Antwort:

- H/B/S/V/R
- contrast
- uncertainty
- absolute_claim
- evidence_marker
- creative_marker
- connection_marker
- long_paragraph
- missing_structure

Es speichert Reports und kann daraus Self-Lessons erzeugen. Es schreibt die Antwort nicht automatisch neu.

## Offline Wiki

Das Offline-Wiki nutzt eine lokale ZIM-Datei:

```text
./wiki/wikipedia_de_all_mini.zim
```

Funktionen:

- automatische Begriffserkennung
- explizite Abfrage mit `/maat wiki <begriff>`
- mehrere Artikel möglich
- Quellenblock wird als Offline-Wiki gekennzeichnet
- Modell soll erkennen: diese Fakten kommen aus lokalem Wiki-Kontext, nicht aus Live-Web

Settings:

- ZIM-Pfad
- Auto an/aus
- Max Artikel
- Zeichen pro Artikel
- Zeichen Multi-Artikel
- Debug

## Project Memory

Project Memory trennt Forschungswissen von persönlichen Erinnerungen.

Projektfelder:

- Name
- Tags
- Beschreibung
- Kontext
- Trigger
- Formeln
- Papers
- Einträge

Beispiele:

```text
/maat project add MAAT ToE|toe,cosmology,cci|Observable-Constrained Structural Selection Theory
/maat project formula add MAAT ToE|R_rob|min(R_resp,(H*B*S*V)^0.25)|Robustheitsgrenze
/maat project paper add MAAT ToE|Paper 43|Zenodo/Academia|Notizen
```

Bei passenden Begriffen wird Projektkontext automatisch in den Prompt geladen.

## Docs / File Builder

Der File Builder erkennt Dateiwünsche und Codeblöcke:

- Python
- LaTeX
- HTML
- Text

Funktionen:

- Datei speichern
- Code im Chat anzeigen
- Python-Syntax prüfen
- Python ausführen
- Terminal-Ausführung, wenn aktiviert
- LaTeX zu PDF kompilieren
- PDF/Datei zum Download anbieten
- Fehlerfeedback für die nächste KI-Antwort injizieren

Thinking-Code soll nicht als Datei gespeichert werden.

### Python-Ausführung aktivieren

Python-Ausführung ist aus Sicherheitsgründen standardmäßig deaktiviert. Aktivieren nur, wenn du lokal arbeitest und dem erzeugten Code vertraust.

Über die UI:

1. Settings öffnen.
2. MAAT / Docs / File Builder Bereich öffnen.
3. `Aktiv` eingeschaltet lassen.
4. `Python ausführen` aktivieren.
5. Optional `Im Terminal` aktivieren, wenn `.py`-Dateien in einem sichtbaren Terminalfenster laufen sollen.
6. Speichern.

Alternativ in `data/settings.json`:

```json
{
  "file_builder_python_run_enabled": true,
  "file_builder_python_run_in_terminal": false
}
```

Wenn `file_builder_python_run_in_terminal` auf `true` steht, versucht MAAT Web Core ein lokales Terminal zu öffnen. Wenn es auf `false` steht, wird der Code im Python-Prozess/Environment des Web Core ausgeführt und das Ergebnis in der UI angezeigt.

## Commands

Allgemein:

```text
/help
/maat help
/maat status
```

Memory:

```text
/maat memory
/maat memory recall <suchtext>
/maat memory save <text>
/maat memory search <query>
/maat memory stats
/maat graph
/maat person <name>
/maat timeline
/maat milestones
```

ChatSearch:

```text
/maat search <query>
/maat search stats
/maat search rebuild
suche im chat nach musicgen
finde chat über CCI
wann haben wir über MAAT Pinball gesprochen?
```

ChatSearch nutzt `data/chat_search.sqlite` als lokalen SQLite-FTS5-Index. Web-Core-Chats
und optional konfigurierte externe Chatlog-Ordner werden durchsucht, ohne sie ins SuperMemory
zu schreiben. Suchturns, Progress-Karten, Thinking-Blöcke und interne MAAT-Blöcke werden
beim Indexieren bereinigt.

Learning / Feedback:

```text
/maat lessons
/maat lessons add <category>|<type>|<lesson>
/maat feedback
/maat feedback test <text>
/maat why
```

Project / Docs:

```text
/maat project
/maat project add <name>|<tags>|<beschreibung>
/maat project save <projekt>|<typ>|<text>
/maat project formula add <projekt>|<name>|<formel>|<beschreibung>
/maat project paper add <projekt>|<titel>|<ref>|<notizen>
/maat docs
/maat docs last
```

MAAT Control:

```text
/maat core mode light|standard|strict
/maat reality
/maat time
/maat date
/maat balance preview <text>
/maat claim test <text>
/maat rewrite
/maat engine eval <text>
/maat cci eval <text>
/maat reflection
/maat antihallu evalq <frage> || <antwort>
/maat identity
/maat style
/maat emotion
/maat spirit
/maat wiki <begriff>
```

## API

Wichtige Endpunkte:

```text
GET  /api/state
GET  /api/chats
GET  /api/chat?chat_id=<id>
POST /api/chat/stream
POST /api/settings
GET  /api/help
GET  /api/log
GET  /api/gguf-models
POST /api/system-scan
POST /api/system-scan/apply
```

Weitere Endpunkte existieren für:

- Project Memory
- Docs/File Builder
- SuperMemory Person Graph
- Memory Dreaming
- Chat-Verwaltung

Streaming läuft über Server-Sent Events.

## Datenablage

Standard:

```text
data/settings.json
data/maat_web.sqlite
data/docs/
```

Per Environment umleitbar:

```bash
export MAAT_WEB_HOME="/pfad/zum/datenordner"
export MAAT_WEB_PLUGINS="/pfad/zu/plugins"
```

Damit kann die App selbst portabel bleiben, während Daten extern liegen.

## Projektstruktur

```text
maat-web-core/
├── run.py
├── setup.sh
├── start.sh
├── setup.command
├── start.command
├── requirements.txt
├── README.md
├── backend/
│   ├── app.py
│   ├── server.py
│   ├── chat_loop.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   ├── static/
│   ├── maat_super_memory.py
│   ├── maat_context_optimizer.py
│   ├── maat_chat_compressor.py
│   ├── maat_offline_wiki.py
│   ├── maat_project_memory.py
│   ├── maat_file_builder.py
│   └── maat_*.py
├── data/
└── plugins/
```

## Plugin Hooks

Plugins liegen in:

```text
plugins/<plugin_name>/plugin.py
```

Ein Plugin kann Hooks anbieten:

```python
class Plugin:
    type = "chat"
    commands = {"/meinbefehl": "Beschreibung"}

    def on_startup(self, context): ...
    def before_chat(self, user_input, context): ...
    def before_final_response(self, reply, context): ...
    def after_response(self, reply, context): ...
    def after_final_response(self, reply, context): ...
    def command(self, cmd, context): ...
```

## Debugging

Empfohlene Debug-Schalter:

- SuperMemory Debug
- Offline Wiki Debug
- Context Optimizer Debug
- Compressor Debug
- Project Memory Debug
- File Builder Debug
- Engine Debug vor Antwort
- Advanced CCI Debug

Im Log-Tab siehst du dann, welcher Kontext wirklich im Prompt gelandet ist.

## Typischer Entwicklungsablauf

1. Modell im Settings- oder Chatfenster wählen.
2. User im Chatfenster setzen.
3. Bei langen Chats Compressor aktiv lassen.
4. Context Optimizer aktiv lassen.
5. SuperMemory Debug nur bei Tests einschalten.
6. Offline Wiki Debug einschalten, wenn Quellen geprüft werden.
7. File Builder Debug einschalten, wenn Code/LaTeX nicht erkannt wird.
8. `/maat status` oder Help-Tab nutzen, wenn ein Modul unklar ist.

## Rechtliches und Lizenzen

Dieser Abschnitt ist eine technische Orientierung und keine Rechtsberatung. Vor einer öffentlichen Veröffentlichung, kommerziellen Nutzung oder Weitergabe mit vorinstallierten Modellen/Wiki-Daten sollten die jeweiligen Lizenzen und Nutzungsbedingungen geprüft werden.

### Projektlizenz

Der MAAT-Web-Core-Code steht unter der **GNU Affero General Public License v3.0**. Der vollständige Lizenztext liegt in [LICENSE](LICENSE).

Kurz gesagt:

- Du darfst den Code nutzen, studieren, ändern und weitergeben, solange du die AGPL-3.0-Bedingungen einhältst.
- Wenn du eine geänderte Version über ein Netzwerk als Dienst anbietest, müssen Nutzerinnen und Nutzer die Möglichkeit erhalten, den entsprechenden Quellcode dieser Version zu bekommen.
- Abgeleitete Versionen müssen unter kompatiblen Bedingungen weitergegeben werden.
- Es gibt keine Gewährleistung; Nutzung erfolgt auf eigene Verantwortung.

Die AGPL passt hier bewusst, weil MAAT Web Core ein webbasiertes lokales/serverfähiges Tool ist und Verbesserungen am Webdienst nicht unsichtbar proprietär eingeschlossen werden sollen.

Referenz: <https://www.gnu.org/licenses/agpl-3.0.html>

### Drittkomponenten

Python-Pakete, JavaScript-Dateien, Schriftarten und andere Abhängigkeiten behalten jeweils ihre eigenen Lizenzen. Details stehen in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Besonders wichtig:

- `llama-cpp-python`, `PyMuPDF`, `KaTeX` und weitere Pakete werden nicht vom MAAT-Projekt lizenziert, sondern nur genutzt.
- Das lokal eingebundene KaTeX-Material steht unter MIT-Lizenz. Lizenz- und Copyright-Hinweise müssen bei Weitergabe erhalten bleiben.
- Modellgewichte, Tokenizer, GGUF-Dateien und Wiki/ZIM-Dateien sind keine Bestandteile dieses Repositorys.

### Modelle

Das Setup kann optional GGUF-Modelle herunterladen. Diese Downloads passieren nur nach Zustimmung und über `huggingface_hub` direkt von den jeweiligen Originalquellen, z.B. Hugging Face.

Für Modelle gilt:

- Die jeweilige Modelllizenz ist maßgeblich, nicht die Lizenz dieses Repos.
- Vor Redistribution, Upload, Bundle-Builds oder kommerzieller Nutzung muss die Modellkarte geprüft werden.
- Wenn Modelle später mit einer App ausgeliefert werden, müssen deren Lizenz- und Notice-Pflichten separat erfüllt werden.

Für die aktuell vorgeschlagenen Gemma-4-GGUF-Downloads verweist die genutzte Hugging-Face-Modellkarte auf Apache-2.0. Das kann sich ändern oder durch konkrete Modelldateien/Upstream-Bedingungen ergänzt werden.

Nützliche Referenzen:

- Gemma-4-GGUF-Modellkarte: <https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF>
- Apache License 2.0: <https://www.apache.org/licenses/LICENSE-2.0>

### Offline Wiki / Kiwix / Wikipedia

Das Setup kann optional eine deutsche Wikipedia-ZIM-Datei von Kiwix herunterladen. Dieses Repository liefert keine ZIM-Dateien mit.

Für Wiki-Inhalte gilt:

- Wikipedia-Text steht typischerweise unter CC BY-SA 4.0 und GFDL, inklusive Attribution- und Share-Alike-Pflichten.
- Medien/Bilder in Wiki-Dumps können andere Lizenzen haben.
- Wer ZIM-Dateien weiterverteilt oder daraus Inhalte veröffentlicht, muss die jeweiligen Wikimedia-/Kiwix-/openZIM-Bedingungen beachten.

Referenz: <https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use>

### Datenschutz und externe Verbindungen

MAAT Web Core ist standardmäßig lokal gedacht. Trotzdem können Daten das Gerät verlassen, wenn du es so konfigurierst:

- Modell- oder ZIM-Downloads kontaktieren Hugging Face bzw. Kiwix.
- Der OpenAI-kompatible Adapter sendet Prompts an den eingestellten API-Endpunkt. Das kann lokal sein, muss es aber nicht.
- Wenn der Server im LAN oder Internet erreichbar ist, sollte Passwortschutz aktiviert und die Firewall passend gesetzt werden.

Keine privaten Memories, Chatlogs, Projektdateien oder Dokumente sollten in ein Public Repo übernommen werden.

### Generierte Inhalte

Antworten, Code, LaTeX, PDFs, Zusammenfassungen und Analysen werden von lokalen oder angebundenen KI-Modellen erzeugt und können falsch, unvollständig, voreingenommen oder rechtlich problematisch sein.

Die Nutzung erfolgt auf eigene Verantwortung. MAAT Web Core ersetzt keine medizinische, rechtliche, finanzielle oder sicherheitskritische Fachberatung.

### Marken und Namen

Namen wie Gemma, Hugging Face, Kiwix, Wikimedia, Wikipedia, KaTeX, Python und llama.cpp gehören ihren jeweiligen Rechteinhabern. Die Erwähnung bedeutet keine Unterstützung, Partnerschaft oder Zertifizierung durch diese Projekte.

KaTeX-Lizenzreferenz: <https://github.com/KaTeX/KaTeX/blob/main/LICENSE>

## Aktuelle Grenzen

- Die H/B/S/V/R-Werte sind heuristisch, keine objektive Wahrheit.
- Direkter GGUF-Loader hängt stark von `llama-cpp-python`, Build, Modellfamilie und RAM ab.
- Qwen-3.6-, Gemma-4- und LFM-Kompatibilität ist best effort und kann je nach GGUF/llama.cpp-Version variieren.
- Rewrite Loop muss bei Code/LaTeX vorsichtig eingesetzt werden.
- Offline Wiki ist lokal, nicht Live-Web.
- SuperMemory speichert nur, was erkannt oder explizit gespeichert wird.

## Philosophie

MAAT Web Core ist nicht nur ein Chat-Frontend. Es ist eine lokale Architektur für:

- Erinnerung
- Kontextbewusstsein
- Quellenbewusstsein
- Denkregeln
- Projektwissen
- Selbstdiagnose
- praktische Datei-/Codearbeit

Kurz:

```text
Memory speichert Ereignisse.
Lessons speichern Denkregeln.
Project Memory speichert Forschungswissen.
Context Optimizer entscheidet, was in den Prompt darf.
MAAT Engine prüft, ob die Antwort strukturell stabil ist.
```
