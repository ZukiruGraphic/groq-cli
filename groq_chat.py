import sys
if "--help" in sys.argv or "-h" in sys.argv:
    print("groq v1.0 - Groq CLI")
    print("")
    print("Usage:")
    print('  groq                  open chat')
    print('  groq "hello"          quick use')
    print('  groq -m "your-model"  choose model')
    print('  groq -k "your-keys"   create keys')
    print("  groq --version        show version")
    print("  groq --help           show this help")
    print("")
    print('  groq -m               show current model')
    print('  groq -k               show current key')
    print("")
    print("Inside chat:")
    print("  .h help  .q quit  .c clear  @file read file")
    print("")
    print("Details:")
    print('  -m "your-model"')
    print("    Choice a model from")
    print("    groq websites.")
    print('  -k "your-keys"')
    print("    Create your keys and")
    print("    copy it from groq")
    print("    websites.")
    sys.exit(0)
if "--version" in sys.argv:
    print("v1.0")
    sys.exit(0)
import os, json, textwrap, argparse, threading, time, pathlib
import requests
from prompt_toolkit import PromptSession
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style
GREEN = "\033[38;2;0;255;0m"
MODEL_GREEN = "\033[38;2;162;230;180m"
PINK_PASTEL = "\033[38;2;255;182;193m"
CYAN = "\033[36m"
DIM = "\033[90m"
RESET = "\033[0m"
LOADING = "\033[38;2;233;213;255m"
SPINNER = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
MODEL = "openai/gpt-oss-20b"
CFG = pathlib.Path("/data/data/com.termux/files/home/groq/config.json")
def load_cfg():
    if CFG.exists():
        try:
            return json.loads(CFG.read_text())
        except:
            return {}
    return {}
def save_cfg(m=None, k=None):
    c = load_cfg()
    if m:
        c["model"] = m
    if k:
        c["api_key"] = k
    CFG.write_text(json.dumps(c))
    return c
_cfg = load_cfg()
if _cfg.get("model"):
    MODEL = _cfg["model"]
if _cfg.get("api_key"):
    os.environ["GROQ_API_KEY"] = _cfg["api_key"]
class SlashAtLexer(Lexer):
    def lex_document(self, document):
        line = document.lines[0] if document.lines else ""
        def get_line(lineno):
            toks = []
            i = 0
            while i < len(line):
                c = line[i]
                if c == "@":
                    j = i + 1
                    while j < len(line) and (line[j].isalnum() or line[j] in "/._-"):
                        j += 1
                    toks.append(("class:at", line[i:j]))
                    i = j
                elif c == ".":
                    j = i + 1
                    while j < len(line) and line[j].isalnum():
                        j += 1
                    toks.append(("class:slash", line[i:j]))
                    i = j
                else:
                    toks.append(("class:input", c))
                    i += 1
            return toks
        return get_line
style = Style.from_dict({"input": "#FFFFFF", "prompt": "#5EEAD4", "cursor": "#5EEAD4", "slash": "#666666", "at": "#7DE6FF", "dim": "#666666"})
def W():
    try:
        return os.get_terminal_size().columns
    except:
        return 60

import re as _re2
def _vis(s):
    return len(_re2.sub(r"\[[0-9;]*m", "", s))
def _wrap_ansi(text, width, indent="  "):
    # wrap tapi ngitung panjang visible doang, ANSI gak dihitung
    words = text.split(" ")
    lines, cur, cur_len = [], indent, len(indent)
    # potong kata panjang tanpa spasi jadi chunk per lebar
    _words = []
    for _w in words:
        while _vis(_w) > max(20, W()-2) - len(indent):
            _cut = max(20, W()-2) - len(indent)
            _words.append(_w[:_cut])
            _w = _w[_cut:]
        _words.append(_w)
    words = _words
    for w in words:
        wl = _vis(w)
        if cur_len + (1 if cur != indent else 0) + wl > width and cur != indent:
            lines.append(cur)
            cur, cur_len = indent + w, len(indent) + wl
        else:
            if cur != indent:
                cur += " "
                cur_len += 1
            cur += w
            cur_len += wl
    if cur.strip():
        lines.append(cur)
    return lines
def render_md(out):
    # HTML di dalem tabel: <ul><li> -> bullet, tag lain ilangin
    out = out.replace("<ul>", "").replace("</ul>", "")
    out = out.replace("<li>", "• ").replace("</li>", "\n  ")
    out = _re2.sub(r"<(em|i)>", "*", out)
    out = _re2.sub(r"</(em|i)>", "*", out)
    out = _re2.sub(r"<(strong|b)>", "**", out)
    out = _re2.sub(r"</(strong|b)>", "**", out)
    out = _re2.sub(r"<[^>]+>", "", out)
    import html as _html
    out = _html.unescape(out)
    out = out.replace("<br>", "\n  ").replace("<br/>", "\n  ").replace("<br />", "\n  ")
    lines = []
    in_code = False
    for raw in out.split("\n"):
        s = raw.strip()
        # codeblock ``` toggle
        if s.startswith("```"):
            in_code = not in_code
            lines.append("  [90m```[0m")
            continue
        if in_code:
            # semua abu-abu, wrap tetep jalan
            for l in _wrap_ansi("[90m" + raw + "[0m", max(20, W()-2)):
                lines.append(l)
            continue
        if not s:
            lines.append("")
            continue
        # skip garis |---|---| tabel, cuma pemisah, gak ada info
        if set(s) <= set("|-: ") and "-" in s and "|" in s:
            continue
        # heading ## / ### -> bold, # ilang
        if s.startswith("#"):
            s = _re2.sub(r"^#+\s*", "", s)
            s = f"[1m{s}[0m"
        # inline: **bold**, *italic*, `code`
        s = _re2.sub(r"\*\*(.+?)\*\*", r"[1m\1[0m", s)
        s = _re2.sub(r"(?<!\*)\*([^\*]+?)\*(?!\*)", r"[3m\1[0m", s)
        s = _re2.sub(r"`([^`]+?)`", r"[90m\1[0m", s)
        for l in _wrap_ansi(s, max(20, W()-2)):
            lines.append(l)
    return "\n".join(lines)

def header():
    import os as _o
    _o.system("chafa --size 40x10 /data/data/com.termux/files/home/groq/logo.png")
    print(f"  {CYAN}Groq CLI {RESET}{DIM}v1.0{RESET}")
    print("")
    print(f"  {DIM}Authenticated with groq-api-key /auth{RESET}")
    print("")
    print(f"  {DIM}Tips for getting started:{RESET}")
    print("  1. Type [38;2;125;230;255m@filename[0m to read a file")
    print("  2. [90m.h[0m to see commands")
    print("  3. Ask about coding, edit code, or run a command")
    print("  4. Be specific for the best results")
    print("")
    print(f"  {DIM}Shift+Tab to accept edits{RESET}")
    print("")
    _path = "/data/data/com.termux/files/home"
    _model = MODEL
    print(f"  {DIM}workspace (/directory){RESET}" + " " * (len(_path) + 2 - len("workspace (/directory)")) + f"{DIM}model{RESET}")
    print(f"  [38;2;242;217;140m{_path}[0m  [38;2;168;230;161m{_model}[0m")
    print("")
def input_in_box():
    sess = PromptSession(lexer=SlashAtLexer(), style=style, wrap_lines=True, prompt_continuation=lambda width, line_number, is_soft_wrap: "      ")
    q = sess.prompt([("class:dim", "  │ "), ("class:prompt", "❯ ")])
    return q
def call_groq(msgs, box):
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        print('  API key not set. groq -k "your-keys"')
        return
    stop = threading.Event()
    def spin():
        i = 0
        while not stop.is_set():
            _k = (i // 5) % 4
            dots = "." * _k + " " * (3 - _k)
            sys.stdout.write(f"\r{LOADING}  {SPINNER[i % len(SPINNER)]} Generating{dots}   {RESET}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
    th = threading.Thread(target=spin)
    th.start()
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json={"model": MODEL, "messages": msgs}, timeout=60)
        stop.set()
        th.join()
        sys.stdout.write("\r\033[K")
        if r.status_code != 200:
            print(f"  error {r.status_code}: {r.text[:200]}")
            return
        out = r.json()["choices"][0]["message"]["content"]
        import re as _re
        out = _re.sub(r"", "", out, flags=_re.S).strip()
        print(f"  {PINK_PASTEL}Groq{RESET}")
        print(render_md(out))
    except Exception as e:
        stop.set()
        th.join()
        sys.stdout.write("\r\033[K")
        print(f"  error: {e}")
_parser = argparse.ArgumentParser(prog="groq")
_parser.add_argument("-m", "--model", nargs="?", const="__SHOW__")
_parser.add_argument("-k", "--key", nargs="?", const="__SHOW__")
_parser.add_argument("prompt", nargs="?")
_args, _ = _parser.parse_known_args()
if _args.model == "__SHOW__":
    print(f"current model: {MODEL}")
    sys.exit(0)
if _args.model:
    save_cfg(m=_args.model)
    print(f"model changed to: {_args.model}")
    sys.exit(0)
if _args.key == "__SHOW__":
    _k = os.getenv("GROQ_API_KEY", "") or _cfg.get("api_key", "")
    if not _k:
        print("no key set. groq -k \"your-keys\"")
    else:
        print(f"current key: {_k[:7]}...{_k[-4:]}")
    sys.exit(0)
if _args.key:
    save_cfg(k=_args.key)
    print("API key changed & saved")
    sys.exit(0)
if _args.prompt:
    call_groq([{"role": "user", "content": _args.prompt}], False)
    sys.exit(0)
header()
msgs = []
while True:
    q = input_in_box()
    qs = q.strip()
    if qs == ".":
        print("  .h help  .q quit  .c clear  @file read file")
        print("")
        continue
    core = qs[1:] if qs.startswith(".") else qs
    if core in ("q", "quit", "exit"):
        break
    if core in ("h", "help"):
        print("  .h help  .q quit  .c clear  @file read file")
        print("")
        continue
    if core in ("c", "clear", "cls"):
        import os as _o
        _o.system("clear")
        header()
        continue
    if not qs:
        continue
    extra = ""
    if "@" in qs:
        import re as _re, pathlib as _pl
        for m in _re.findall(r"@([A-Za-z0-9/._-]+)", qs):
            fp = _pl.Path(m).expanduser()
            if not fp.is_absolute():
                fp = pathlib.Path("/data/data/com.termux/files/home") / m
            if fp.exists() and fp.is_file():
                try:
                    extra += f"\n\nFile {m}:\n{fp.read_text()[:8000]}"
                except:
                    pass
            elif fp.exists() and fp.is_dir():
                extra += f"\n\nFolder {m}: " + ", ".join([x.name for x in fp.iterdir()][:50])
            else:
                print(f"  file not found: {m}")
    print("")
    print(textwrap.fill(f"{DIM}You: {qs}{RESET}", width=max(20, W()-2), initial_indent="  ", subsequent_indent="     "))
    print("")
    msgs.append({"role": "user", "content": qs + extra})
    call_groq(msgs, False)
    print("")
