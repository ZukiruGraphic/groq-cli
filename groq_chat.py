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
    print("  .h help  .q quit  .c clear  .w write  .e edit  .d delete  @current folder  @file read file")
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
# AI optimasi: system prompt + ingatan chat + temp rendah buat code biar gak ngarang
SYSTEM_PROMPT = """You are Groq CLI in Termux, a helpful coding assistant.
CRITICAL LANGUAGE RULE - LANGUAGE LOCK - HIGHEST PRIORITY:
- You MUST reply in the EXACT same language as the user's LAST message.
- If user writes in English, reply in English ONLY. NEVER switch to Indonesian.
- If user writes in Indonesian, reply in Indonesian ONLY. NEVER switch to English.
- If user writes in mixed casual Indonesian, reply in SAME mixed casual Indonesian.
- Never switch language mid-conversation unless user CLEARLY switches first.
- Do NOT use location / IP / timezone to guess language. Use ONLY user's last message.
- Code stays in English, but ALL explanation MUST stay in user's language.
- If you are about to reply in different language than user's last message, STOP and rewrite in user's language.
CODE RULES - MUST FOLLOW:
- If user asks for code, output code MUST be valid, complete, and runnable directly.
- If file is .py, print MUST use () and quotes, example print("test2"). NEVER print without ().
- Do NOT invent file content if user did not give content, say you do not know.
- Answer short, dense, do NOT ramble."""

HISTORY = []
MAX_HISTORY = 10
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


import re as _re3
def _clean_code(out):
    # buang ```python / ``` biar yang ke-save cuma isi file-nya doang
    out = out.strip()
    out = _re3.sub(r"^```[a-zA-Z0-9]*\n", "", out)
    out = _re3.sub(r"\n```\s*$", "", out)
    out = out.strip()
    return out
def _parse_target(qs):
    import re as _rx
    m = _rx.search(r"@([A-Za-z0-9/._-]+)", qs)
    base = m.group(1) if m else ""
    # cari nama file: "nama filenya X" ATAU "file X" ATAU "hello.py" yang ada .py/.txt/.md
    fn = _rx.search(r"nama filenya ([A-Za-z0-9/._-]+)", qs, _rx.I)
    if not fn:
        fn = _rx.search(r"file ([A-Za-z0-9_.-]+[.][A-Za-z0-9]+)", qs, _rx.I)
    if not fn:
        # fallback: cari kata yang ada .py/.txt/.md/.js di qs, yang bukan @groq-nya
        for _w in qs.split():
            _w = _w.strip(",.")
            if "." in _w and _w.split(".")[-1] in ("py","txt","md","js","html","css","json"):
                if _w != base and not _w.startswith("@"):
                    fn = type("O", (), {"group": lambda s, i=1: _w})()
                    break
    fname = fn.group(1) if fn else ""
    # kalau fname masih kosong tapi base-nya file (ada .py), base itu file-nya
    if not fname and "." in base and "/" not in base:
        pass
    return base, fname
def _resolve_path(base, fname):
    import pathlib as _pl
    home = _pl.Path("/data/data/com.termux/files/home")
    cwd = _pl.Path.cwd()
    # kalau base-nya folder di home (groq), dan fname ada (hello.py), gabung jadi home/groq/hello.py
    # @current/xxx = folder sekarang, bukan folder namanya current
    if base == "current" or base.startswith("current/"):
        import pathlib as _pc
        _cwd = _pc.Path.cwd()
        if base == "current":
            if fname:
                return _cwd / fname
            return _cwd
        _rest = base[len("current/"):]
        if fname and _rest.endswith(fname):
            return _cwd / _rest
        if fname:
            return _cwd / _rest / fname
        return _cwd / _rest
    if base and fname:
        # base bisa folder, cek home dulu biar gak kena file nyasar ~/groq/groq
        _hb = home / base
        if _hb.is_dir():
            return _hb / fname
        _cb = cwd / base
        if _cb.is_dir():
            return _cb / fname
        # base-nya file, fname-nya yang bener, pake parent base + fname
        if _hb.parent.is_dir():
            return _hb.parent / fname
        return cwd / fname
    if fname:
        return cwd / fname if (cwd / fname).exists() else home / fname
    if base:
        # base doang, tanpa fname: kalau base ada .py, itu file, kalau gak ada, itu folder
        _hb = home / base
        if _hb.exists():
            return _hb
        _cb = cwd / base
        if _cb.exists():
            return _cb
        return _hb
    return None


def _sub(msg):
    # subtext abu-abu, 2 spasi, path SELALU di bawah text-nya
    print("")
    _s = str(msg).strip()
    if "/data/" in _s:
        import re as _rs
        # "Writing to /data/..." / "Done, file written to /data/..." / "Done, file edited: /data/..." -> pisah 2 baris
        _m = _rs.match(r"^(.*?to)\s+(/data/.*)$", _s)
        if not _m:
            _m = _rs.match(r"^(.*?edited:)\s+(/data/.*)$", _s)
        if not _m:
            _m = _rs.match(r"^(.*?deleted:)\s+(/data/.*)$", _s)
        if not _m:
            _m = _rs.match(r"^(Writing to|Editing)\s+(/data/.*)$", _s)
        if _m:
            print(f"\033[90m  {_m.group(1)}\033[0m")
            print(f"\033[90m  {_m.group(2)}\033[0m")
            print("")
            return
        # fallback: kalau ada /data/ tapi pattern gak ketemu, pisah manual di /data/
        _idx = _s.find("/data/")
        print(f"\033[90m  {_s[:_idx].strip()}\033[0m")
        print(f"\033[90m  {_s[_idx:]}\033[0m")
        print("")
        return
    print(f"\033[90m  {_s}\033[0m")
    print("")

def _detect_lang(qs):
    try:
        low = " " + str(qs).lower().replace(",", " ").replace(".", " ").replace("?", " ").replace("!", " ") + " "
        id_words = [" yang ", " adalah ", " dan ", " dengan ", " untuk ", " dari ", " ini ", " itu ", " kenapa ", " gimana ", " bagaimana ", " tolong ", " bikin ", " buat ", " gw ", " lu ", " gue ", " kamu ", " saya ", " apa ", " dimana ", " kapan ", " berapa ", " jangan ", " udah ", " belum ", " lagi ", " sama ", " kayak ", " banget ", " dong ", " sih ", " kok ", " nih ", " tuh ", " aja ", " nggak ", " gak ", " benerin ", " masih ", " suka ", " keluar ", " sendiri ", " bahasa ", " dipake ", " dipakai ", " jelasin ", " sejarah "]
        en_words = [" what ", " how ", " why ", " when ", " where ", " which ", " please ", " tell ", " explain ", " more ", " details ", " about ", " history ", " usage ", " hello ", " thanks ", " can ", " you ", " the ", " is ", " are ", " groq ", " python ", " details "]
        id_n = sum(1 for w in id_words if w in low)
        en_n = sum(1 for w in en_words if w in low)
        if id_n > en_n:
            return "Indonesian"
        if en_n > 0:
            return "English"
        return "English"
    except:
        return "English"

def _print_groq_answer(ans):
    print("\r" + " " * 50 + "\r", end="")
    print("")
    # nama + text SAMA indent-nya: 2 spasi, biar sejajar
    print("  \033[38;2;255;182;193mGroq\033[0m")
    try:
        _out = render_md(ans)
        for _l in _out.splitlines():
            # buang indent bawaan render_md, terus kasih 2 spasi yang sama kayak nama-nya
            print("  " + _l.lstrip() if _l.strip() else "")
    except:
        import textwrap as _tw2, shutil as _sh2
        _w2 = _sh2.get_terminal_size().columns - 4
        for _l in _tw2.wrap(ans, width=max(30, _w2), break_long_words=False, break_on_hyphens=False):
            print("  " + _l)
    print("")
def _show_loading():
    import threading as _th, time as _ti, sys as _sy
    _stop = {"v": False, "th": None}
    _icons = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    def _run():
        _i = 0
        while not _stop["v"]:
            # icon cepet 0.12s, titik lambat 0.5s: titik ganti tiap 4x icon (0.12 x 4 = 0.48s)
            _dots = "." * (((_i // 4) % 3) + 1)
            _sy.stdout.write(f"\r  \033[38;2;233;213;255m{_icons[_i % len(_icons)]} Loading{_dots}   \033[0m")
            _sy.stdout.flush()
            _ti.sleep(0.12)
            _i += 1
        _sy.stdout.write("\r" + " " * 50 + "\r")
        _sy.stdout.flush()
    _th.Thread(target=_run, daemon=True).start()
    return _stop
def _stop_loading(_st):
    # stop + tunggu thread-nya bener-bener kelar, baru lanjut, biar gak numpuk
    import time as _ti2
    if not _st:
        return
    _st["v"] = True
    _ti2.sleep(0.6)
    print("\r" + " " * 50 + "\r", end="")
def _groq_short(prompt):
    try:
        _r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY','')}", "Content-Type": "application/json"}, json={"model": MODEL, "messages": [{"role": "user", "content": prompt}]}, timeout=30)
        return _r.json()["choices"][0]["message"]["content"].strip()
    except Exception as _e:
        return ""

def _fix_py_print(code, fname):
    # fix85 yang bolong: Groq sering ngeluarin print "xxx" Python 2, benerin jadi print("xxx") Python 3
    import re as _r
    out = []
    for _line in code.splitlines():
        _m = _r.match(r"^(\s*)print\s+([\"\'].*[\"\'])\s*$", _line)
        if _m:
            out.append(f"{_m.group(1)}print({_m.group(2)})")
            continue
        _m2 = _r.match(r"^(\s*)print\s+([^\(].*)$", _line)
        if _m2 and "print(" not in _line:
            out.append(f"{_m2.group(1)}print({_m2.group(2).strip()})")
            continue
        out.append(_line)
    return "\n".join(out)

def header():
    import os as _o
    _w = max(40, min(50, W()-4))
    _h = min(12, max(10, _w // 4))
    _o.system(f"chafa --size {_w}x{_h} /data/data/com.termux/files/home/groq/logo.png")
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
            sys.stdout.write(f"\r{LOADING}  {SPINNER[i % len(SPINNER)]} Loading{dots}   {RESET}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
    th = threading.Thread(target=spin)
    th.start()
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json={"model": MODEL, "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + HISTORY[-10:] + msgs, "temperature": 0.7, "max_tokens": 2000}, timeout=60)
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
        print("  .h help  .q quit  .c clear  .w write  .e edit  .d delete  @current folder  @file read file")
        print("")
        continue
    core = qs[1:] if qs.startswith(".") else qs
    if core in ("q", "quit", "exit"):
        break
    if core in ("h", "help"):
        print("  .h help  .q quit  .c clear  .w write  .e edit  .d delete  @current folder  @file read file")
        print("")
        continue
    if core in ("c", "clear", "cls"):
        import os as _o
        _o.system("clear")
        header()
        continue
    if core.startswith("d ") or core == "d":
        import re as _rd
        _targets = _rd.findall(r"@([A-Za-z0-9/._-]+)", qs)
        # kalau gak ada @, coba cari nama file-nya aja
        if not _targets:
            _b2, _f2 = _parse_target(qs)
            _targets = [(_b2 + "/" + _f2) if _b2 and _f2 else (_f2 or _b2)]
            _targets = [x for x in _targets if x]
        if not _targets:
            print("  .d need @file. contoh: .d hapus file @groq/hello.txt  /  .d @current/hello.py dan @current/hello.txt")
            print("")
            continue
        for _tg in _targets:
            # @current/hello.py -> cwd/hello.py, @groq/hello.py -> home/groq/hello.py
            if _tg == "current":
                _all_d = _rd.findall(r"[A-Za-z0-9_.-]+\.py", qs)
                if len(_all_d) > 1:
                    import pathlib as _pd1
                    _deleted = []
                    for _fn in _all_d:
                        _tg1 = _pd1.Path.cwd() / _fn
                        if _tg1.exists() and not _tg1.is_dir():
                            _tg1.unlink()
                            _deleted.append(_fn)
                            _sub(f"Done, file deleted: {_tg1}")
                    _isi = qs
                    _ld = _show_loading()
                    _ans3 = _groq_short(f"Give a short response in the SAME language as user: {_detect_lang(qs)}, bilang file {', '.join(_deleted)} udah dihapus semua.")
                    _stop_loading(_ld)
                    if _ans3:
                        _print_groq_answer(_ans3)
                    # skip blok single-file di bawah, biar gak double hapus + gak print sampah cannot delete folder
                    _all_d = []
                    continue
                if _all_d:
                    import pathlib as _pd0
                    _tgt0 = _pd0.Path.cwd() / _all_d[0]
                    if _tgt0.exists() and not _tgt0.is_dir():
                        _tgt0.unlink()
                        _sub(f"Done, file deleted: {_tgt0}")
                        _ld = _show_loading()
                        _ans3 = _groq_short(f"Give a short response in the SAME language as user: {_detect_lang(qs)}, bilang file {_tgt0.name} udah dihapus.")
                        _stop_loading(_ld)
                        if _ans3:
                            _print_groq_answer(_ans3)
                    else:
                        print(f"  .d file not found: {_tgt0}")
                else:
                    print("  .d cannot delete folder current, sebutin file-nya: @current/hello.py")
                continue
            if _tg.startswith("current/"):
                import pathlib as _pd
                _target = _pd.Path.cwd() / _tg[len("current/"):]
            else:
                _b3, _f3 = _parse_target("@" + _tg)
                _target = _resolve_path(_b3, _f3) if _b3 else None
                if not _target:
                    import pathlib as _pd2
                    _target = _pd2.Path("/data/data/com.termux/files/home") / _tg
            if not _target or not _target.exists():
                _sub(f"  .d file not found: {_target}")
                continue
            if _target.is_dir():
                _sub(f"  .d cannot delete folder: {_target}")
                continue
            _target.unlink()
            _sub(f"Done, file deleted: {_target}")
            _ld = _show_loading()
            _ans3 = _groq_short(f"Give a short response with markdown **bold** for filename and `code` for commands, in the SAME language as user: {_detect_lang(qs)} - reply ONLY in that language. Use markdown: **bold** for filename, `code` for commands like `python3 hi.py`. User request: {qs} 1 kalimat in the SAME language as user: {_detect_lang(qs)} - reply ONLY in that language. Use markdown: **bold** for filename, `code` for commands like `python3 hi.py`. User request: {qs}, bilang file {_target.name} udah dihapus, udah gak ada lagi. DO NOT mention @current.")
            _stop_loading(_ld)
            if _ans3:
                _print_groq_answer(_ans3)
        print("")
        continue
    if core.startswith("w ") or core == "w":
        # .w multi-file: satu.py, dua.py, tiga.py - tiap file dapet prompt sendiri, bukan digabung ke 1 file
        import re as _rm
        _all = _rm.findall(r"[A-Za-z0-9_.-]+\.py", qs)
        if len(_all) > 1:
            # potong qs per file: dari satu.py sampe sebelum dua.py, dst
            _pos = [(m.group(0), m.start()) for m in _rm.finditer(r"[A-Za-z0-9_.-]+\.py", qs)]
            for _idx, (_fn, _st) in enumerate(_pos):
                _en = _pos[_idx+1][1] if _idx+1 < len(_pos) else len(qs)
                _seg = qs[_st:_en]
                _seg = _seg.replace(_fn, "").replace("buat file", "").replace("buat", "").replace("file", "").replace("isi", "").replace("di @current", "").replace("@current", "").replace(",", "").strip()
                _tgt = pathlib.Path.cwd() / _fn
                _sub(f"  Writing to {_tgt} ...")
                _pr = f"Create file content for {_fn}. Instruction: {_seg}. Output HANYA isi file-nya doang, tanpa penjelasan, tanpa markdown."
                _ld1 = _show_loading()
                _r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY','')}", "Content-Type": "application/json"}, json={"model": MODEL, "messages": [{"role": "user", "content": _pr}]}, timeout=60)
                _stop_loading(_ld1)
                _out = _clean_code(_r.json()["choices"][0]["message"]["content"])
                _tgt.parent.mkdir(parents=True, exist_ok=True)
                _tgt.write_text(_out)
                _sub(f"Done, file written to {_tgt}")
                globals()["LAST_FILE"] = str(_tgt)
            _isi = qs
            _ld = _show_loading()
            _ans = _groq_short(f"Give a short response in the SAME language as user: {_detect_lang(qs)}, bilang file {', '.join(_all)} udah dibikin, tiap file isinya beda sesuai permintaan, cara jalaninnya pake python3 <nama file>. User request: {qs}")
            _stop_loading(_ld)
            if _ans:
                _print_groq_answer(_ans)
            print("")
            continue
        _base, _fname = _parse_target(qs)
        _target = _resolve_path(_base, _fname)
        if not _target:
            print("  .w butuh @path + nama filenya. contoh: .w buatin file di path @groq nama filenya test.py, mau diisi hello world")
            print("")
            continue
        # kalau .w gak ada nama file-nya, _target-nya folder, jangan write_text ke folder
        if not _target or _target.is_dir() or not _fname:
            _fn = _groq_short(f"Give ONLY a filename like hello.py for this request: {qs}. No explanation, only filename.")
            _fn = _fn.strip().split()[0].strip('`.,')
            if not _fn.endswith('.py'):
                _fn = 'hello.py'
            _base_dir = _target if _target and _target.is_dir() else pathlib.Path.cwd()
            _target = _base_dir / _fn
            _fname = _fn
        _sub(f"  Writing to {_target} ...")
        _prompt = f"Create file content for {_target.name}. Instruction dari user: {qs}. Output HANYA isi file-nya doang, tanpa penjelasan, tanpa markdown ```, tanpa kata-kata lain."
        _ld1 = _show_loading()
        _r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY','')}", "Content-Type": "application/json"}, json={"model": MODEL, "messages": [{"role": "user", "content": _prompt}]}, timeout=60)
        _stop_loading(_ld1)
        _out = _clean_code(_r.json()["choices"][0]["message"]["content"])
        _target.parent.mkdir(parents=True, exist_ok=True)
        _target.write_text(_out)
        _sub(f"Done, file written to {_target}")
        globals()["LAST_FILE"] = str(_target)
        _isi = qs
        _ld = _show_loading()
        _ans = _groq_short(f"Give a short response with markdown **bold** for filename and `code` for commands, in the SAME language as user: {_detect_lang(qs)} - reply ONLY in that language. Use markdown: **bold** for filename, `code` for commands like `python3 hi.py`. User request: {qs} 1-2 kalimat in the SAME language as user: {_detect_lang(qs)} - reply ONLY in that language. Use markdown: **bold** for filename, `code` for commands like `python3 hi.py`. User request: {qs}, bilang file {_target.name} udah dibikin, isinya tentang {_isi[:200]}, cara jalaninnya pake python3 {_target.name}, DO NOT mention @current, JANGAN sebut kata file pertama. Do not output code-nya lagi.")
        _stop_loading(_ld)
        if _ans:
            _print_groq_answer(_ans)
        print("")
        continue
    if core.startswith("e ") or core == "e":
        import re as _re2
        # .e multi-file: satu.py jadi ..., dua.py jadi ..., tiga.py jadi ... - tiap file dapet isi sendiri
        _all_e = _re2.findall(r"[A-Za-z0-9_.-]+\.py", qs)
        if len(_all_e) > 1 and "@" not in qs.replace("@current", ""):
            _pos = [(m.group(0), m.start()) for m in _re2.finditer(r"[A-Za-z0-9_.-]+\.py", qs)]
            for _idx, (_fn, _st) in enumerate(_pos):
                _en = _pos[_idx+1][1] if _idx+1 < len(_pos) else len(qs)
                _seg = qs[_st:_en]
                _seg = _seg.replace(_fn, "").strip()
                import re as _rc
                _seg = _rc.sub(r"^(jadi|edit)\s+", "", _seg, flags=_rc.I).strip()
                _seg = _seg.replace("di @current", "").replace("@current", "").replace(",", "").strip()
                _tgt = pathlib.Path.cwd() / _fn
                if not _tgt.exists():
                    _sub(f"  .e file not found: {_tgt}")
                    continue
                _old = _tgt.read_text()
                _sub(f"  Editing {_tgt} ...")
                _pr = f"Edit file {_fn} SAJA, jadiin isi-nya: {_seg}. Isi lama: {_old[:12000]}. Output HANYA isi file baru-nya doang, tanpa penjelasan, tanpa markdown."
                _ld1 = _show_loading()
                _r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY','')}", "Content-Type": "application/json"}, json={"model": MODEL, "messages": [{"role": "user", "content": _pr}]}, timeout=60)
                _stop_loading(_ld1)
                _out = _fix_py_print(_clean_code(_r.json()["choices"][0]["message"]["content"]), _fn)
                _tgt.write_text(_out)
                _sub(f"Done, file edited: {_tgt}")
            _ld = _show_loading()
            _ans2 = _groq_short(f"Give a short response in the SAME language as user: {_detect_lang(qs)}, bilang file {', '.join(_all_e)} udah di-edit semua, tiap file isinya beda sesuai permintaan. User request: {qs}")
            _stop_loading(_ld)
            if _ans2:
                _print_groq_answer(_ans2)
            print("")
            continue
        # parse per-file: @current/tes_a.py jadi print("a99") dan file @current/tes_b.py jadi print("b99")
        _per_e = _re2.findall(r"@([A-Za-z0-9/._-]+)\s+jadi\s+(.+?)(?=\s+dan\s+file\s+@|\s*$)", qs, _re2.I)
        _jobs_e = []
        if len(_per_e) >= 2:
            for _tg, _isi_e in _per_e:
                import pathlib as _pe
                if _tg.startswith("current/"):
                    _tgt = _pe.Path.cwd() / _tg[len("current/"):]
                else:
                    _tgt = _pe.Path("/data/data/com.termux/files/home") / _tg
                _jobs_e.append((_tgt, _isi_e.strip()))
        else:
            _tgs2 = _re2.findall(r"@([A-Za-z0-9/._-]+)", qs)
            for _tg in _tgs2:
                if _tg == "current":
                    _b0, _f0 = _parse_target(qs)
                    if _f0:
                        import pathlib as _pe0
                        _tgt0 = _pe0.Path.cwd() / _f0
                        _jobs_e.append((_tgt0, qs))
                    continue
                import pathlib as _pe2
                if _tg.startswith("current/"):
                    _tgt = _pe2.Path.cwd() / _tg[len("current/"):]
                else:
                    _bb, _ff = _parse_target("@" + _tg)
                    _tgt = _resolve_path(_bb, _ff) if _bb else _pe2.Path("/data/data/com.termux/files/home") / _tg
                _jobs_e.append((_tgt, qs))
        if not _jobs_e:
            print("  .e need @file. contoh: .e editin file @groq/a.py dan @groq/b.py ganti jadi merah")
            print("")
            continue
        for _target, _isi_e in _jobs_e:
            if not _target or not _target.exists() or not _target.is_file():
                _sub(f"  .e file not found: {_target}")
                continue
            _old = _target.read_text()
            _sub(f"  Editing {_target} ...")
            _prompt = f'Edit file {_target.name} SAJA, jangan edit file lain. Jadiin isi-nya: {_isi_e}. Isi lama: {_old[:12000]}. Output HANYA isi file baru-nya doang, 1 file ini aja, tanpa penjelasan, tanpa markdown.'
            _ld1 = _show_loading()
            _r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY','')}", "Content-Type": "application/json"}, json={"model": MODEL, "messages": [{"role": "user", "content": _prompt}]}, timeout=60)
            _stop_loading(_ld1)
            _out = _fix_py_print(_clean_code(_r.json()["choices"][0]["message"]["content"]), _target.name)
            _target.write_text(_out)
            _sub(f"Done, file edited: {_target}")
            _ld = _show_loading()
            _ans2 = _groq_short(f"Give a short response with markdown **bold** for filename and `code` for commands, in the SAME language as user: {_detect_lang(qs)} - reply ONLY in that language. Use markdown: **bold** for filename, `code` for commands like `python3 hi.py`. User request: {qs} 1-2 kalimat in the SAME language as user: {_detect_lang(qs)} - reply ONLY in that language. Use markdown: **bold** for filename, `code` for commands like `python3 hi.py`. User request: {qs}, bilang file {_target.name} udah di-edit jadi {_isi_e[:200]}, cara ceknya pake python3 {_target.name}, DO NOT mention @current. Do not output code-nya lagi.")
            _stop_loading(_ld)
            if _ans2:
                _print_groq_answer(_ans2)
        print("")
        continue
    HISTORY.append({"role": "user", "content": qs})
    HISTORY[:] = HISTORY[-MAX_HISTORY:]
    if not qs:
        continue
    extra = ""
    # auto @current: kasih list file cwd ke AI, biar gak perlu ketik @current terus
    try:
        _cwd_files = [x.name for x in pathlib.Path.cwd().iterdir()][:20]
        extra += f"\n\nCurrent folder {pathlib.Path.cwd()}: " + ", ".join(_cwd_files)
        if LAST_FILE:
            extra += f"\nLast file: {LAST_FILE}"
    except:
        pass
    _skip_current = ("@current" in qs)
    # @current / @. / @ doang = folder sekarang
    if "@current" in qs or "@." in qs or qs.strip() == "@" or " @" in qs or qs.strip().startswith("@ "):
        import pathlib as _plc
        _cwd = _plc.Path.cwd()
        _files = [x.name for x in _cwd.iterdir()][:50]
        extra += f"\n\nCurrent folder {_cwd}: " + ", ".join(_files)
        # kalau ada hello.py di cwd, kirim juga isinya biar gak ngarang
        for _fn in ["hello.py", "hello.txt"]:
            _fp = _cwd / _fn
            if _fp.is_file():
                try:
                    extra += f"\n\nFile {_fn}:\n{_fp.read_text()[:8000]}"
                except:
                    pass
    if "@" in qs:
        import re as _re, pathlib as _pl
        for m in _re.findall(r"@([A-Za-z0-9/._-]+)", qs):
            fp = _pl.Path(m).expanduser()
            if not fp.is_absolute():
                _cwd = pathlib.Path.cwd() / m
                _home = pathlib.Path("/data/data/com.termux/files/home") / m
                fp = _cwd if _cwd.exists() else _home
            if fp.exists() and fp.is_file():
                try:
                    extra += f"\n\nFile {m}:\n{fp.read_text()[:8000]}"
                except:
                    pass
            elif fp.exists() and fp.is_dir():
                extra += f"\n\nFolder {m}: " + ", ".join([x.name for x in fp.iterdir()][:50])
            else:
                if _skip_current or "current" in qs.lower():
                    pass
                else:
                    print(f"  file not found: {m}")
    print("")
    print(textwrap.fill(f"{DIM}You: {qs}{RESET}", width=max(20, W()-2), initial_indent="  ", subsequent_indent="     "))
    print("")
    msgs.append({"role": "user", "content": qs + extra})
    call_groq(msgs, False)
    print("")