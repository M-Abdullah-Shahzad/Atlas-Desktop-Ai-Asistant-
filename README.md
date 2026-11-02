# Atlas Desktop AI Assistant

Atlas is a personal AI desktop assistant designed to help you interact with your computer through natural voice conversations and practical tools. Instead of being limited to a chat window, Atlas can understand requests, work with files, interact with desktop applications, search the web, and connect with supported services.

The assistant uses **Gemini Live** for real-time voice interaction and provides a **PyQt6 desktop HUD** for voice, typed commands, activity, and results.

> Atlas is actively developed. Available features depend on your operating system, installed applications, API credentials, and integration setup.

## What Atlas can do

### Voice assistant and conversation

- Real-time voice conversations using Gemini Live.
- Typed commands through the desktop interface.
- Natural spoken responses with input and output transcription.
- English as the default response language, with explicit language switching.
- Configurable assistant and user names.
- Voice interruption, mute, and response controls.
- Automatic reconnection for supported transient network and service failures.
- Session summaries and learned corrections.

### Desktop interface

- Animated PyQt6 HUD with listening, thinking, speaking, sleeping, and error states.
- Activity log and a content panel for search results, code, tables, news, and file output.
- Drag-and-drop file input.
- Camera preview and live camera view.
- Clipboard panel for copied content.
- Fullscreen and system-tray modes.
- Desktop shortcut creation on supported operating systems.
- Optional morning briefing and configurable content-panel visibility.

### Screen understanding and vision

- Capture and analyze the current desktop screen.
- Capture and analyze webcam frames.
- Keep a live camera preview open while needed.
- Start and stop user-consented live screen sharing.
- Share screen images during an active conversation when requested.
- Protection against repeated or overlapping vision requests.

Screen sharing sends visual captures; it does not share computer audio.

### Computer control

Atlas can perform supported desktop actions, including:

- Open applications and manage windows.
- Adjust volume and brightness.
- Access Wi-Fi and supported system settings.
- Manage browser tabs, zoom, refresh, scrolling, and keyboard shortcuts.
- Type text, click, double-click, right-click, move the mouse, and use copy/paste.
- Find and interact with visible screen elements.
- Capture screenshots.
- Browse File Explorer.
- Run CMD and PowerShell commands, including optional administrator execution.
- Lock, sleep, restart, or shut down the computer through confirmation-gated actions.

The available controls depend on the operating system and installed applications.

### File management

- List, open, read, create, and edit files.
- Rename, move, copy, paste, and delete files.
- Create folders and search for files.
- Inspect disk usage and find large files.
- Organize desktop files.
- Work with paths across available drives.
- Process files dropped into or uploaded through the interface.

### File and document processing

Atlas provides supported workflows for common file types:

| File type | Available workflows |
|---|---|
| Images | Describe, OCR, resize, compress, convert, and inspect metadata |
| PDF | Summarize, extract text, inspect, and convert to Word |
| Word and text | Summarize, reformat, count words, and organize content |
| CSV and Excel | Analyze, calculate statistics, filter, sort, and convert |
| JSON and XML | Validate, format, analyze, and convert JSON to CSV |
| Source code | Explain, review, fix, optimize, run, document, and test |
| Audio | Transcribe, trim, convert, and inspect |
| Video | Trim, extract audio or frames, compress, transcribe, and convert |
| Archives | List and extract contents |
| Presentations | Summarize, extract text, and analyze |

The exact operations available depend on installed tools and the input file.

### Data viewer

- Display CSV, TSV, JSON, JSONL, Parquet, and Excel data as tables.
- Limit visible rows and columns.
- Inspect the first or last rows.
- Navigate large datasets with row offsets.
- Select columns and sort values.
- Show tabular results in the desktop content panel.

### Web search and browser control

- Search the web for general information, news, research, prices, and comparisons.
- Use supported search engines, including Google, Bing, DuckDuckGo, and Yandex.
- Open URLs in supported browsers.
- Navigate backward and forward, reload pages, and open tabs.
- Click elements, enter text, fill forms, and scroll pages.
- Extract visible page text, read the current URL, and capture browser screenshots.
- Work with supported installations of Chrome, Edge, Firefox, Opera, Opera GX, Brave, Vivaldi, and Safari where available.

Browser automation depends on the installed browser and its available automation support.

### Connected services

**WhatsApp**
- Connect through a local Baileys bridge and QR-based device linking.
- Resolve contacts and groups, including phone-number lookup.
- Compose messages before sending.
- Send text, media, documents, screenshots, and voice notes.
- Read chat history and check unread chats.
- Support incoming-message monitoring and configurable direct-message auto-replies.
- Import contacts from VCF and Google CSV files.

WhatsApp setup from source requires Node.js 18+ and the packages listed in `whatsapp_bridge/package.json`.

**Gmail**
- Compose and send messages through the Gmail API after Google OAuth setup.
- Review a draft before sending or cancel the send workflow.

**Spotify**
- Play tracks, artists, playlists, and liked songs.
- Pause, resume, skip, and control shuffle and repeat.
- Requires Spotify Desktop and Web API authorization. Playback may require a Spotify Premium account.

**YouTube**
- Search for and play videos.
- Retrieve video information and summarize supported video content.
- View trending videos by region.
- Save summaries to Notepad when requested.

### Everyday utilities

- Weather reports by city.
- Flight searches with route and trip details.
- Timed reminders through Windows Task Scheduler.
- Steam and Epic Games installation, update, status, and scheduling controls.
- Optional computer shutdown after a game update completes.
- Wallpaper controls and desktop cleanup, organization, and statistics.

### System monitoring and proactive assistance

- Monitor CPU, RAM, GPU, temperature, battery, disk, network, uptime, and processes.
- Report high-resource processes and watch selected processes.
- Provide configurable proactive check-ins.
- Monitor user-configured news topics and deliver supported alerts.
- Send background WhatsApp alerts when configured.
- Learn local application routines and tool outcomes, with controls to inspect or forget learned habits.

### Memory and personalization

- Maintain persistent context for preferences, projects, notes, and routines.
- Update memory when the user explicitly shares relevant information.
- Create session summaries and record corrections.
- Keep response-language state during a session.
- Use relevant context in startup greetings and briefings.

### Phone dashboard and remote controls

- Run a local web dashboard using FastAPI and Uvicorn.
- Relay phone microphone input to the active voice session and return assistant audio.
- Send remote text commands.
- Approve or deny permission requests remotely.
- Control mute, interruption, sleep, wake, and supported settings.
- Upload files and receive live status, log, content, and permission events over WebSockets.
- Connect through QR or manual connection details, with local HTTPS and remote-connection configuration support.

### MetaTrader 5 market analysis

When a MetaTrader 5 terminal is available, Atlas can:

- Check connection status.
- Retrieve supported symbol quotes, including bid, ask, and spread.
- Analyze supported symbols and timeframes using technical indicators.
- Provide a BUY, SELL, or WAIT bias as analysis, not as an instruction to trade.
- Retrieve economic-calendar and relevant news context.
- Capture and analyze chart snapshots.
- Monitor the connection and record structured connection events.

**The MetaTrader 5 integration is read-only. Atlas does not place trades, submit orders, or manage trading positions.**

## Permissions and safety

Atlas uses risk levels to manage tool execution:

- **Low risk:** may run automatically when the configured policy allows it.
- **Medium and high risk:** require confirmation through supported voice, typed, or remote controls.
- **Critical actions:** may be blocked by policy.
- Computer sleep, restart, and shutdown actions use confirmation.

You can approve or cancel supported actions using the confirmation controls. Avoid granting permissions to actions you do not understand.

## Requirements

For the full feature set, use:

- Windows 10 or Windows 11.
- Python 3.11 or 3.12.
- A working microphone for voice interaction.
- Internet access for Gemini Live and online integrations.
- A Gemini API key.

Additional requirements are integration-specific:

- **WhatsApp:** Node.js 18+ when running from source.
- **MetaTrader 5:** an installed and configured MetaTrader 5 terminal.
- **Gmail:** Google OAuth credentials and API setup.
- **Spotify:** Spotify Desktop and Web API authorization.
- **Remote dashboard:** network access and the required local or remote connection configuration.

Some operating-system actions are Windows-specific. Other platform support depends on the relevant application and integration.

## Getting started

1. Install Python 3.11 or 3.12.
2. Clone this repository and open a terminal in the project directory.
3. Install the Python dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Start Atlas:

   ```bash
   python main.py
   ```

5. On the first run, use the setup prompt in the desktop interface to provide your Gemini API key.

The application stores the key in `config/api_keys.json`. Keep this file private and do not commit it to source control.

## Optional integration setup

### WhatsApp

1. Open **Settings → WhatsApp Setup** in Atlas.
2. Scan the QR code using WhatsApp's **Linked Devices** option.
3. Import contacts when you want spoken contact names to resolve more reliably.

When setting up the bridge manually from source:

```bash
cd whatsapp_bridge
npm install
npm start
```

Atlas can also start the local bridge itself when the required dependencies are available.

### Gmail

Configure the Gmail API and Google OAuth credentials, then run the login flow:

```bash
python actions/gmail_bridge_client.py --login
```

### Spotify

Install and sign in to Spotify Desktop, then complete the Web API authorization when prompted. The login helper is also available:

```bash
python actions/spotify_control.py --login
```

Other integrations can be configured from their relevant settings and setup screens.

## Project structure

```text
.
├── main.py                 # Assistant runtime and tool routing
├── ui.py                   # PyQt6 desktop HUD
├── core/                   # Prompts, permissions, and shared logic
├── actions/                # Desktop, file, web, and service integrations
├── config/                 # Local configuration and API key settings
├── dashboard/              # Phone and remote dashboard
├── whatsapp_bridge/        # Local WhatsApp bridge
├── memory/                 # Local memory and session data
├── tests/                  # Project tests
├── requirements.txt        # Python dependencies
└── setup.py                # Package setup
```

## Local dashboard TLS

Atlas generates a self-signed TLS certificate and a fresh private key locally on first dashboard startup. The key is stored under `config/certs/atlas-local.key` and is excluded from Git. A browser may show a trust warning because this certificate is self-signed; do not treat it as a publicly trusted certificate.

For a certificate issued by your own CA, set both `ATLAS_TLS_KEY_FILE` and `ATLAS_TLS_CERT_FILE` to local file paths before starting Atlas. Do not commit private keys. Legacy `atlas.key` and `jarvis.key` files are intentionally not used.

## Local WhatsApp contacts

WhatsApp contacts are private local data. Import your own `.vcf` or `.csv` files into `Contacts/`; Atlas rebuilds `memory/contacts_index.json` locally from those files. The generated index is ignored by Git and should never be committed.

## Limitations and privacy notes

- Gemini Live and most online integrations require an internet connection.
- Feature availability depends on API access, credentials, installed applications, and operating-system support.
- WhatsApp requires a valid linked-device session.
- Gmail requires Google OAuth configuration.
- Spotify playback depends on account access and authorization.
- Browser and vision features depend on available browser automation and successful screen or camera capture.
- MetaTrader 5 support is limited to analysis and connection monitoring; it does not execute trades.
- API keys, OAuth tokens, linked-device sessions, and personal memory files are sensitive local data. Keep them private and out of public commits.

---

Atlas is a work in progress. Features and integrations may change as development continues.
