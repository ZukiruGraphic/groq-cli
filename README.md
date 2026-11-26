# **Groq CLI v1.0**
A minimal Groq CLI for Termux, styled like Gemini CLI.

Install Dependencies - Copy-Paste This:
```bash
pkg install python chafa -y && pip install requests prompt_toolkit
```

What it installs:
- python - to run groq_chat.py
- chafa - to show logo.png in header
- requests - to call Groq API
- prompt_toolkit - for input, highlight, wrapping

If pip fails, try:
```bash
pip install --break-system-packages requests prompt_toolkit
```

Features:
- **Chat mode** with `groq`
- **Quick use** with `groq "hello"`
- **File reading** with `@filename`
- **Markdown:** **bold**, *italic*, `code`, tables, codeblocks
- Wrapped responses, wrapped input, wrapped You: subtext
- Pastel colors, PNG logo header via chafa
- Shortcuts: .h help, .q quit, .c clear, . for help
- Check model / key with groq -m and groq -k

Files:
- groq_chat.py - main script
- logo.png - header logo, must be at $HOME/groq/logo.png
- README.md - this file
- INSTALL.txt - quick install guide

Do NOT put config.json in upload. It contains your API key.

Setup:
```bash
alias groq="python3 $HOME/groq/groq_chat.py"
source ~/.bashrc
groq -k "your-keys"
groq -m "your-model"
Get key from [Groq Console](https://console.groq.com) - API Keys - Create.
Free model: `openai/gpt-oss-20b`
```

Usage:
groq - open chat
groq "hello" - quick use
groq -m "your-model" - choose model
groq -k "your-keys" - save API key
groq -m - show current model
groq -k - show current key (masked)
groq --version - show version
groq --help - show help

Inside chat: .h help .q quit .c clear @file read file

Logo - Why It Needs chafa:
- File: $HOME/groq/logo.png (must be exactly here)
- Tool: chafa - renders PNG in terminal
- Run: chafa --size 40x10 $HOME/groq/logo.png
- If logo does not show, check: ls -1 $HOME/groq/logo.png and chafa --version
- Without chafa, chat still works, logo will not show.
- Without logo.png, chat still works, chafa will error.

Notes:
- Workspace is /data/data/com.termux/files/home
- Model and key are saved in $HOME/groq/config.json
- Key shown by groq -k is masked, only first 7 + last 4 chars

## Official Links
- **Groq:** https://groq.com
- **Groq Console:** https://console.groq.com
- **Groq Docs:** https://console.groq.com/docs
