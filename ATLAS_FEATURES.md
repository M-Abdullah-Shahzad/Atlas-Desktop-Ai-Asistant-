# Atlas Features

> Atlas is the name of this project and assistant.
>
> This repository is a personal desktop assistant. It is not the separate trading-desk project.

## 1. Core Assistant

- Gemini Live voice conversation with native audio input and output.
- Typed commands through the desktop HUD.
- English as the default response language.
- Explicit language switching with session language handling.
- Configurable assistant name and user name.
- Natural spoken responses with input and output transcription.
- Automatic reconnect handling for transient Gemini and network failures.
- API key setup and reconfiguration from the UI.
- Session summaries and learned tool/style corrections.

## 2. Desktop HUD

- PyQt6 desktop interface with animated assistant HUD.
- Listening, thinking, speaking, sleeping, and error states.
- Activity log mirrored to the existing `logs/athena.log` compatibility path.
- Content panel for search results, generated code, tables, news, and file results.
- Drag-and-drop file area for uploaded files.
- Camera preview and live camera stream.
- Clipboard panel with actions for copied content.
- Mute toggle, interrupt control, fullscreen mode, and tray mode.
- Desktop shortcut creation on Windows, macOS, and Linux where supported.
- Configurable morning briefing and content-panel visibility.

## 3. Vision and Screen Tools

- Capture and analyze the current desktop screen.
- Capture and analyze a webcam frame.
- Keep a live camera preview open until it is closed.
- Start and stop user-consented live screen sharing.
- Send current screen stills while the user is speaking.
- Protect against repeated or overlapping vision requests.
- Screen sharing sends pictures only; it does not share computer audio.

## 4. Computer Control

- Open applications.
- Control volume and brightness.
- Control Wi-Fi and other supported computer settings.
- Manage windows, fullscreen mode, tabs, zoom, refresh, scrolling, and keyboard shortcuts.
- Type text, click, double-click, right-click, press keys, move the mouse, copy, and paste.
- Find and click visible screen elements.
- Take screenshots.
- Lock the computer.
- Sleep, restart, or shut down the PC through confirmation-gated actions.
- Close applications by name.
- Run CMD or PowerShell commands, including optional administrator execution.
- Browse File Explorer visually.

## 5. File Management

- List, open, read, create, write, rename, move, copy, paste, delete, and find files.
- Create folders and inspect disk usage.
- Find large files.
- Organize the desktop.
- Work with paths on multiple drives, including drive letters and volume labels.
- Use the Windows clipboard for copy and paste workflows.
- Process dropped or uploaded files.

## 6. File Processing

Supported file workflows include:

- Images: describe, OCR, resize, compress, convert, and inspect metadata.
- PDF files: summarize, extract text, convert to Word, and inspect.
- Word and text files: summarize, fix, reformat, translate guidance, count words, and convert to bullets.
- CSV and Excel files: analyze, calculate statistics, filter, sort, and convert.
- JSON and XML: validate, format, analyze, and convert JSON to CSV.
- Source code: explain, review, fix, optimize, run, document, and test.
- Audio: transcribe, trim, convert, and inspect.
- Video: trim, extract audio, extract frames, compress, transcribe, inspect, and convert.
- Archives: list and extract.
- Presentations: summarize, extract text, and analyze.

## 7. Data Viewer

- Render CSV, TSV, JSON, JSONL, Parquet, and Excel files as structured tables.
- Limit displayed rows and columns.
- Show the first or last rows.
- Offset into large datasets.
- Select columns.
- Sort by a column in ascending or descending order.
- Display tables in the HUD content panel.

## 8. Web and Browser Features

- Web search modes: normal search, news, research, price lookup, and comparison.
- Search-engine selection including Google, Bing, DuckDuckGo, and Yandex where supported.
- Open URLs in supported browsers.
- Browser search, navigation, back, forward, reload, and new tabs.
- Click, type, smart-click, smart-type, form filling, scrolling, and text extraction.
- Read the current URL and take browser screenshots.
- Switch between browser sessions and close tabs or browsers.
- Support for Chrome, Edge, Firefox, Opera, Opera GX, Brave, Vivaldi, and Safari where available.

## 9. Communication Integrations

### WhatsApp

- Local Baileys bridge for WhatsApp Web protocol access.
- QR linking through the WhatsApp Setup panel.
- Contact and group name resolution.
- Phone-number resolution with country code.
- Compose messages before sending.
- Send text, media, documents, screenshots, and voice notes.
- Read chat history and list unread chats.
- Abort pending drafts.
- DM-only auto-reply mode.
- Incoming WhatsApp event monitoring.
- Contact imports from VCF and Google CSV files.

WhatsApp source setup requires Node.js 18+ and the packages in `whatsapp_bridge/package.json`.

### Gmail and Other Messaging

- Gmail API message composition and sending after OAuth setup.
- Support hooks for Telegram, Discord, and other configured messaging platforms.
- Draft, send, or abort workflow with confirmation for sending.

### Spotify

- Play tracks, artists, playlists, or liked songs.
- Pause, resume, next, and previous.
- Toggle shuffle.
- Set repeat modes.
- Requires Spotify Desktop and Web API authorization for playback.

### YouTube

- Search and play videos.
- Summarize video content.
- Retrieve video information.
- Show trending videos by region.
- Save summaries to Notepad when requested.

## 10. Daily Assistant Services

- Weather reports by city.
- Flight searches with origin, destination, date, return date, passengers, and cabin.
- Timed reminders using Windows Task Scheduler.
- Steam and Epic game installation, updates, status checks, and scheduling.
- Optional shutdown after a game update completes.
- Desktop wallpaper control, cleanup, organization, listing, and statistics.

## 11. MetaTrader 5 Analysis

- Connection status checks.
- Live quotes with bid, ask, and spread.
- Technical analysis for supported symbols and timeframes.
- BUY, SELL, or WAIT bias output.
- Economic calendar and short news context.
- One-time chart snapshot capture and analysis.
- MT5 connection keepalive and structured logs.

**Important limitation:** this repository is read-only for MT5. It never places trades or manages orders. Auto-trading belongs to a separate trading project.

## 12. Monitoring and Proactive Features

- CPU, RAM, GPU, temperature, battery, disk, network, uptime, and process monitoring.
- Optional top-process reporting.
- Process watch and unwatch controls.
- Proactive check-ins after a period of user silence.
- User-configured daily news topic monitoring.
- Background WhatsApp alert delivery.
- Local habit learning for app routines and tool outcomes.
- Enable, disable, inspect, or forget learned habits.

## 13. Memory and Personalization

- Persistent personal memory for identity, preferences, projects, relationships, wishes, notes, and learned routines.
- Silent memory updates for facts the user explicitly shares.
- Session summaries at the end of meaningful sessions.
- Correction logging and learner rollups.
- Response-language session state.
- Conversation context used in startup greetings and briefings.

## 14. Phone and Remote Dashboard

- Local web dashboard served through FastAPI and Uvicorn.
- Phone microphone relay into the Gemini Live session.
- Athena audio relay back to the phone.
- Remote text commands.
- Remote permission approval and denial.
- Remote mute, interrupt, sleep, wake, and configuration controls.
- Remote file upload support up to the configured limit.
- WebSocket event updates for logs, status, content, and permissions.
- Local HTTPS/remote configuration support with encrypted command transport.
- QR or manual connection information for the dashboard.

## 15. Permission and Safety Controls

- Risk levels: low, medium, high, and critical.
- Automatic execution for low-risk actions when allowed.
- Confirmation for medium- and high-risk actions.
- Confirmation through voice, typed input, or the remote dashboard.
- Grant phrases such as `go ahead`, `permission granted`, and `proceed`.
- Abort phrases such as `abort`, `cancel`, and `stop`.
- Configurable confirmation timeout.
- Critical actions can be denied by policy.
- Duplicate tool-call protection after an action has completed.
- PC shutdown, restart, and sleep actions use a confirmation overlay.

## 16. Sleep, Wake, and Shutdown

- Sleep mode hides the HUD and keeps Athena running in the system tray.
- Wake through the tray icon or configured wake word.
- Wake greeting after returning from sleep.
- Shutdown command saves session information and exits the application.
- Shutting down Athena is separate from shutting down the computer.

## 17. Packaging and Deployment

- PyInstaller onedir build configuration.
- Optional bundled Node.js runtime for WhatsApp builds.
- Bundled WhatsApp bridge dependencies during the build process when npm is available.
- Bundled FFmpeg support for voice-note conversion.
- Hidden-import collection for the Python integrations.
- Windows no-console process handling.
- Application icon and desktop shortcut support.

## 18. Main Requirements

- Windows 10 or 11 for the full feature set.
- Python 3.11 or 3.12 recommended by the project documentation.
- Microphone for voice control.
- Gemini API key.
- Node.js 18+ for WhatsApp when running from source.
- Optional MetaTrader 5 terminal for MT5 analysis.
- Optional credentials or setup for Gmail, Spotify, WhatsApp, remote dashboard, and browser automation.

## 19. Important Limitations

- Internet access is required for Gemini and most web integrations.
- Some operating-system controls are Windows-only.
- WhatsApp requires a live bridge and a valid linked-device session.
- Spotify playback normally requires Premium and authorization.
- Gmail requires Google OAuth configuration.
- Browser automation depends on the installed browser and automation support.
- Vision results depend on successful screen or camera capture.
- MT5 features analyze data only and do not trade.
- Secrets and local session files should remain private and should not be committed.
