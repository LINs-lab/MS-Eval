"""Vendored GT wave parser. MS-Eval/eval imports this file locally.

GT wave structure and lexical node typing for the clean guide pipeline.

Derived from the audited GT parser (source SHA-256
90afb12666ee9042f61572a6df00ee5ae2886bf0110a22db531dd0447f7e8744).
This module only parses text. It does not read dumps, call an LLM, or publish files.
The core applies the approved eight-role/ten-domain vocabulary to its labels.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

# ---------------- 写角色 ----------------

SCRATCH_HANDOFF_RE = re.compile(r"(?i)runtime[-_\s]?unique\b|\bscratch\s+(?:json|file|handoff)\b|\bintermediate\s+(?:json|artifact|file)\b")
DELIVERABLE_RE = re.compile(
    r"(?i)\.(?:xlsx|docx|pptx|csv)\b|\bgoogle\s+sheets?\b|\bgsheet\b|\bnotion\b|\bgform\b|"
    r"\bgoogle\s+forms?\b|\bgoogle\s+calendar\b|\bgcal\b|\be-?mails?\b|\bworkbook\b|\bspreadsheet\b")

WRITE_ROLE_PATTERNS = [
    ("gsheet", [r"\bgsheet\b", r"\bgoogle\s+sheets?\b", r"\bcloud\s+spreadsheet\b"]),
    ("excel", [r"\bexcel\b", r"\.xlsx", r"\bspreadsheet\b", r"\bworkbook\b", r"\bworksheet\b"]),
    ("notion", [r"\bnotion\b", r"\bwiki\b"]),
    ("word", [r"\bword\b", r"\.docx"]),
    ("ppt", [r"\bppt\b", r"\.pptx", r"\bpowerpoint\b", r"\bslides?\b", r"\bpresentation\b"]),
    # 裸 calendar/event/schedule 关键词会误配 “twelve calendar months” 等日期描述；
    # 强句式（动词+event）已由 ACTION_PRIORITY 覆盖，fallback 只认日历写上下文
    ("calendar", [r"\bgcal\b", r"\bgoogle[_\s]?calendar\b", r"calendar\s+event",
                  r"\bcreate[_\s]?event", r"schedul\w*\s+(?:a|an|the|\d+)\s*\w*\s*(?:meeting|session|appointment)"]),
    ("email", [r"\be-?mail\b", r"\bmail\b"]),
    ("gform", [r"\bgform\b", r"\bgoogle\s+forms?\b", r"\bforms?\b"]),
]

_VERB = r"(?:create|build|make|generate|write|send|schedule|update|publish|upload|add|insert|post|dispatch|own|ensure|produce|upsert|bulk[\s-]*write)\w*"

ACTION_PRIORITY = [
    ("ppt", re.compile(r"(?i)\b" + _VERB + r"\b[^.]*\.pptx")),
    ("word", re.compile(r"(?i)\b" + _VERB + r"\b[^.]*\.docx")),
    ("gsheet", re.compile(r"(?i)\b" + _VERB + r"\b[^.]*\b(?:google\s+sheets?|gsheet|cloud\s+spreadsheet)\b")),
    ("excel", re.compile(r"(?i)\b" + _VERB + r"\b[^.]*(?:\.xlsx|\bworkbook\b|\bworksheet\b|\bspreadsheet\b)")),
    ("notion", re.compile(r"(?i)\b" + _VERB + r"\b[^.]*(?:\bnotion\b|\bwiki\b|\bpage\b|\bdatabase\b)")),
    ("gform", re.compile(r"(?i)\b" + _VERB + r"\b[^.]*\b(?:google\s+forms?|gform)\b")),
    ("email", re.compile(r"(?i)\b(?:send|email|mail|notify|distribute|forward)\w*\b[^.]*\b(?:e-?mails?|mail|notification|message|meeting\s+request|announcement|newsletter)\b")),
    ("calendar", re.compile(r"(?i)\b(?:create|schedule|add|book)\w*\b[^.]*\b(?:events?|calendar|appointment)\b")),
]

# ---------------- 读领域 ----------------

READ_DOMAIN_PATTERNS = [
    ("rail_12306", ["12306", "rail", "get-tickets", "get-station-code", "station code", "train"]),
    ("woocommerce", ["woo_", "woocommerce", "woo "]),
    ("yahoo-finance", ["yahoo", "get_stock", "get-stock", "stock_info", "historical_stock",
                        "longname", "ticker", "stock data api", "stock price", "latest close",
                        "googl", "amzn", "jpm", "jnj", "xom", "^dji", "gc=f", "nasdaq", "dow jones"]),
    ("snowflake", ["snowflake", "sql", "run_query", "warehouse", "data warehouse", "select ",
                    "set-based", ".public.", "query over"]),
    ("scholarly-arxiv", ["arxiv", "scholarly", "search-arxiv", "latex", "paper"]),
    ("external-fetch", ["localhost:", "fetch_json", "http://", "https://", "api/data", "endpoint"]),
    ("notion", ["notion", "wiki"]),
    ("youtube", ["youtube", "fireship", "videos_search", "channels_list", "video"]),
    ("playwright-web", ["playwright", "browser", "snapshot", "navigation"]),
    ("howtocook", ["howtocook", "recipe", "dish", "catering", "菜单", "菜品"]),
    ("canvas", ["canvas", "course_id", "course code", "syllabus", "quiz", "assignment",
                 "discussion topic", "enrollment"]),
    ("emails", ["inbox", "search_emails", "read_email", "email thread"]),
    ("github", ["github"]),
    ("filesystem-workspace", []),
]

BACKTICK_FILE_RE = re.compile(r"`([^`]+?\.(?:json|md|pdf|csv|txt|tar\.gz|xlsx|yaml|yml|py))`")
PLAIN_FILE_RE = re.compile(r"(?<![\w/])[\w\-]+\.(?:pdf|csv|txt|xlsx|tar\.gz)\b")

STRONG_RO_RE = re.compile(
    r"(?i)read[\s-]*only|only\s+read|use\s+only\s+read|without\s+(?:creating|writing|modifying)|"
    r"do\s+not\s+write\s+files|do\s+not\s+persist|do\s+not\s+modify\s+the\s+store")

READONLY_RE = re.compile(
    r"(?i)read[\s-]*only|only\s+read|use\s+only\s+read|do\s+not\s+(?:create|update|delete|write|modify|send|persist)|"
    r"without\s+(?:creating|writing|modifying)|do\s+not\s+(?:write\s+files|modify\s+the\s+store|return\s+the\s+\w+\s+rows\s+in\s+chat)")

WRITE_ACTION_RE = re.compile(
    r"(?i)\b" + _VERB + r"\b[^.]*"
    r"(\.xlsx|\.docx|\.pptx|\.pdf|\bworkbook\b|\bworksheet\b|\bspreadsheet\b|\bgoogle\s+sheets?|\bnotion\b|\bwiki\b|"
    r"\bdocument\b|\bpresentation\b|\bslides?\b|\be-?mails?\b|\bmail\b|\bevents?\b|\bcalendar\b|\bgsheet\b|"
    r"\bgoogle\s+forms?\b|\bgform\b|\bannouncements?\b|\bnewsletters?\b)")

WRITE_STRONG_RE = re.compile(r"(?i)\bbulk[\s-]*write\w*|\bupsert\w*|\bupserting\b")

WAVE_HEAD_RE = re.compile(r"(?m)^[ \t]*(?:\d+\.\s+)?\**Wave\s+(\d+)\s*[—–-]")
ITEM_RE = re.compile(r"(?m)^(?:[ \t]*\d+\.\s+|\s*[-*]\s+)")
AFTER_WAVE_RE = re.compile(r"(?im)^[ \t]*after\s+(?:the\s+)?wave\b")
AFTER_WAVE_MID_RE = re.compile(r"(?i)\.\s+after\s+(?:the\s+)?wave\b")
EXPLORE_DECL_RE = re.compile(r"explore\s+sub-?agent", re.I)
CODER_DECL_RE = re.compile(r"\bcoders?\b", re.I)
NO_DISPATCH_RE = re.compile(r"do\s+not\s+dispatch\s+sub-?agents", re.I)
EFFICIENT_RE = re.compile(r"To solve this task efficiently.*", re.S)

MCP_TOOL_RE = re.compile(r"mcp__([a-z0-9_\-]+)__", re.I)


GSHEET_HINT_RE = re.compile(r"(?i)\bgoogle\s+spreadsheets?\b|\bgoogle\s+sheets?\b|\bgsheets?\b|\bcloud\s+spreadsheets?\b")


def write_role(text: str) -> str:
    t = (text or "").lower()
    if GSHEET_HINT_RE.search(t):
        return "gsheet"
    for role, pat in ACTION_PRIORITY:
        if pat.search(t):
            return role
    for role, pats in WRITE_ROLE_PATTERNS:
        if any(re.search(p, t) for p in pats):
            return role
    return "other-write"


def read_domains(text: str) -> set:
    t = (text or "").lower()
    ds = {d for d, pats in READ_DOMAIN_PATTERNS if any(p in t for p in pats)}
    if BACKTICK_FILE_RE.search(text or "") or PLAIN_FILE_RE.search(text or ""):
        ds.add("filesystem-workspace")
    return ds


NEGATION_RE = re.compile(
    r"(?i)\b(no\s+sub-?agent|must\s+not|do\s+not|don't|never|without|not\s+allowed|prohibited|"
    r"does\s+not|should\s+not|may\s+not|it\s+must\s+not)\b")

RETRIEVAL_RE = re.compile(
    r"(?i)\b(search|retrieve|fetch|download|read|inspect|query|queries|paginat|collect|scan|"
    r"resolve|aggregate|exhaust|browse|navigate)\w*")


def positive_text(text: str) -> str:
    """处理否定（"No sub-agent may ..."、"It must not create ..." 等）：只截掉否定词起的部分，保留前半句的合法动作信号。"""
    sents = re.split(r"(?<=[.!?])\s+", text or "")
    keep = []
    for s in sents:
        m = NEGATION_RE.search(s)
        keep.append(s[:m.start()] if m else s)
    return " ".join(x for x in keep if x.strip())


def classify_rw(text: str, declared: str | None) -> str:
    """read/write 语义判定。
    - 强 read-only 措辞（read-only / do not write files 等）压过一切 -> read
    - 剥离否定句后的交付物写动作 -> write（即使存在弱禁用语，禁用语限定的是其他对象）
    - 检索动词倾向 read；声明 explore->read / coder->write；默认 read
    """
    pos = positive_text(text)
    strong_ro = bool(STRONG_RO_RE.search(text or ""))
    weak_ro = bool(READONLY_RE.search(text or ""))
    wa = bool(WRITE_ACTION_RE.search(pos)) or bool(WRITE_STRONG_RE.search(pos))
    retr = bool(RETRIEVAL_RE.search(pos))
    # 暂存回传守卫：runtime-unique JSON 等中间产物 + 检索动作 + 无交付物 -> 读取型收集器
    if (wa and retr and SCRATCH_HANDOFF_RE.search(text or "") and "json" in (text or "").lower()
            and not DELIVERABLE_RE.search(text or "")):
        return "read"
    if strong_ro and not wa:
        return "read"
    if wa:
        return "write"
    if strong_ro or weak_ro:
        return "read"
    if retr:
        return "read"
    if declared == "explore":
        return "read"
    if declared == "coder":
        return "write"
    return "read"


TASKNAME_IN_PATH_RE = re.compile(r"SingleUserTurn-[A-Za-z0-9_.\-]+")


def make_node(text: str, shared: str = "", fallback_domains=None) -> dict:
    cls_text = (text + "\n" + shared).strip()
    # 擦除 dumps 路径中的任务名段（如 ...-gform / ...-notion），避免任务名后缀被当成交付物/写角色线索
    cls_text = TASKNAME_IN_PATH_RE.sub(" ", cls_text)
    pos = positive_text(cls_text)
    declared = None
    if EXPLORE_DECL_RE.search(cls_text):
        declared = "explore"
    elif CODER_DECL_RE.search(cls_text):
        declared = "coder"
    rw = classify_rw(cls_text, declared)
    node = {"declared": declared, "rw": rw, "text": text}
    if rw == "write":
        node["role"] = write_role(pos)
        node["domains"] = sorted(read_domains(cls_text))
    else:
        node["role"] = None
        doms = read_domains(cls_text)
        # 暂存回传节点（runtime-unique 收集器）的工作区文件是 scratch I/O，不算读取领域
        if (SCRATCH_HANDOFF_RE.search(cls_text) and "filesystem-workspace" in doms
                and not re.search(r"(?i)(read|open|parse|load)[^.]{0,80}\.(?:md|txt|pdf|csv|xlsx|docx)",
                                  cls_text)):
            doms.discard("filesystem-workspace")
        if not doms and fallback_domains:
            doms = set(fallback_domains)
            node["domains_from"] = "preamble-fallback"
        node["domains"] = sorted(doms)
    return node


# ---------------- GT 解析 ----------------

_ROWSPEC = r"\d+(?:\s*[,;–-]\s*(?:\.\.\.?|…)?\s*,?\s*\d+)*"
TPL_BULLET_RE = re.compile(r"(?m)^\s*[-*]\s+\*\*(.+?)\*\*(.*)")
TPL_ROWS_RE = re.compile(r"(?i)^(?:Agents?|Assignment\s+rows|Quiz\s+rows|rows?)?\s*(" + _ROWSPEC + r")\s*[—–-]")
PROSE_WAVE_RE = re.compile(r"(?i)Wave\s+(\d+)\s+[^.;]*?\b(?:rows?|subtasks?)\s+(" + _ROWSPEC + r")")


def expand_rows(spec: str) -> set:
    """展开行号 spec：'1-128'、'527,529,...,539'（省略号为独立逗号段）、'89' -> 行号集合。"""
    s = spec.replace("…", "...").replace("–", "-")
    out, nums = set(), []
    pending_dots = False

    def fill_to(b):
        a = nums[-1] if nums else b
        step = (nums[-1] - nums[-2]) if len(nums) >= 2 and nums[-1] > nums[-2] else 1
        step = max(step, 1)
        if a <= b:
            out.update(range(a + step, b + 1, step))
            nums.append(b)

    for part in (p.strip() for p in re.split(r"[,;]", s) if p.strip()):
        part = part.strip(". ") or part
        if set(part) == {"."}:
            pending_dots = True
            continue
        m = re.match(r"^(?:(\d+)\s*)?\.{2,3}\s*(\d+)$", part)
        if m:
            if m.group(1):
                a, b = int(m.group(1)), int(m.group(2))
                out.update(range(a, b + 1))
                nums += [a, b]
            else:
                fill_to(int(m.group(2)))
            pending_dots = False
        elif "-" in part:
            m = re.match(r"^(\d+)\s*-\s*(\d+)$", part)
            if m:
                out.update(range(int(m.group(1)), int(m.group(2)) + 1))
                nums += [int(m.group(1)), int(m.group(2))]
            pending_dots = False
        elif part.isdigit():
            b = int(part)
            if pending_dots:
                fill_to(b)
                pending_dots = False
            else:
                out.add(b)
                nums.append(b)
    return out


def parse_prose_waves(preamble: str, shared_prelude_domains) -> list[dict]:
    """散文式 wave（'Wave N uses one AgentSwarm for rows a-b' / 'Wave 5 dispatches subtasks c-d'）
    + 模板 bullet（'- **Agents 1-526 — Coder score-page template.** ...'）映射为节点。"""
    templates = []
    for m in TPL_BULLET_RE.finditer(preamble):
        title, body = m.group(1).strip(), m.group(2).strip()
        rm = TPL_ROWS_RE.match(title)
        if not rm:
            continue
        rows = expand_rows(rm.group(1))
        if rows:
            templates.append((rows, title + " " + body))
    if not templates:
        return []
    waves = {}
    for m in PROSE_WAVE_RE.finditer(preamble):
        wn = int(m.group(1))
        rows = expand_rows(m.group(2))
        nodes = []
        for trows, ttext in templates:
            inter = rows & trows
            if inter:
                node = make_node("agents=%d | " % len(inter) + ttext, "", shared_prelude_domains)
                node["n_agents"] = len(inter)
                nodes.append(node)
        if nodes and wn not in waves:
            waves[wn] = nodes
    return [{"wave_num": wn, "nodes": nodes} for wn, nodes in sorted(waves.items())]


WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
            "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}


def wave_head_count(head_line: str):
    """从 wave 头行提取声明的子代理数。

    返回 int（静态数）、"dynamic"（"for each/for every" 按需并行，需人工校准）或 None（未声明）。
    模式：dispatch exactly N / each of the N / <数词> Coder owners / N sub-agents 等。
    """
    t = head_line.strip()
    low = t.lower()
    m = re.search(r"(?i)dispatch(?:es)?\s+(?:all\b[^0-9;.:]{0,40}?)?(?:exactly\s+)?(\d+)", t)
    if m:
        return int(m.group(1))
    m = re.search(r"each of the (\d+)", low)
    if m:
        return int(m.group(1))
    word = None
    m = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+"
                  r"(?:independent\s+|literal\s+|verified\s+|live\s+)*"
                  r"[a-z-]*\s*(?:sub-?agents?|coders?|owners?|writers?|workers?|explorers?)", low)
    if m:
        word = WORD_NUM[m.group(1)]
    if word is None:
        m = re.search(r"\b(\d+)\s+(?:[a-z-]+\s+){0,3}?(?:sub-?agents?|coders?|owners?|writers?|workers?|explorers?)", low)
        if m:
            word = int(m.group(1))
    if word is None:
        m = re.search(r"exactly (one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b", low)
        if m:
            word = WORD_NUM[m.group(1)]
    if re.search(r"\bfor (each|every)\b", low):
        # "one X for each ..." = 按需并行（动态）；显式数词 >=2 优先（"six owners, one for each pair"）
        return word if (word is not None and word >= 2) else "dynamic"
    return word



OLD_DISPATCH_RE = re.compile(r"(?m)^(\d+)\.\s+Please dispatch (multiple|a single)\s+([a-zA-Z-]+)\s+sub-agents?\b[^:]*:")
OLD_ITEM_RE = re.compile(r"(?m)^\s*\(\d+\)\.\s+")


def parse_old_dispatch(seg: str, preamble_domains) -> list:
    """旧模板：'1. Please dispatch multiple explore sub-agents to work in parallel on the following sub-tasks:' + (1). (2). 子项。
    每个编号块 = 一个 wave；子项 = 节点。a single ... sub-task 单节点。"""
    ms = list(OLD_DISPATCH_RE.finditer(seg))
    waves = []
    for i, m in enumerate(ms):
        wn = int(m.group(1))
        kind = m.group(2)
        role = m.group(3).lower()
        start = m.end()
        end = ms[i + 1].start() if i + 1 < len(ms) else len(seg)
        block = seg[start:end]
        aw = AFTER_WAVE_RE.search(block)
        if aw:
            block = block[:aw.start()]
        items = [c.strip() for c in OLD_ITEM_RE.split(block) if c.strip()]
        if kind == "a single" and not items and block.strip():
            items = [block.strip()]
        if not items:
            continue
        nodes = [make_node("%s sub-agent: %s" % (role, it), "", preamble_domains) for it in items]
        declared = 1 if kind == "a single" else len(items)
        waves.append((wn, nodes, declared))
    return waves

def parse_gt(text: str) -> list[dict]:
    """返回有序 wave 列表: {"wave_id", "nodes":[node]}。无分解段/明确不委派 -> []。"""
    if not text:
        return []
    m = EFFICIENT_RE.search(text)
    if not m:
        return []
    seg = m.group(0)
    heads = list(WAVE_HEAD_RE.finditer(seg))
    # efficient 段前言（到第一个 wave 头之前）：供空领域读节点回退 & 散文式 wave 提取
    preamble = seg[:heads[0].start()] if heads else seg[-1800:]
    preamble_domains = read_domains(positive_text(preamble[-1800:]))

    waves = []  # [(wave_num, nodes)]
    for i, h in enumerate(heads):
        start = h.end()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(seg)
        block = seg[start:end]
        aw = AFTER_WAVE_RE.search(block)
        if aw:
            block = block[:aw.start()]
        aw2 = AFTER_WAVE_MID_RE.search(block)
        if aw2:
            block = block[:aw2.start()]
        # A prose wave may have no heading colon. A later "Read-only:" or
        # "Return:" is part of the assignment, never a boundary to discard.
        body = block.strip()
        chunks = ITEM_RE.split(body)
        intro = chunks[0].strip()
        items = [c.strip() for c in chunks[1:] if c.strip()]
        # 末个 item 可能黏附 wave 尾部的共享说明段（无缩进起始于列 0），拆出作为共享上下文
        tail = ""
        if items:
            lines = items[-1].splitlines()
            cut = None
            for li, ln in enumerate(lines):
                if li > 0 and ln and not ln[0].isspace():
                    cut = li
                    break
            if cut is not None:
                tail = "\n".join(lines[cut:]).strip()
                items[-1] = "\n".join(lines[:cut]).strip()
        shared = "\n".join(x for x in (intro, tail) if x)
        if not items and body.strip():
            items = [body.strip()]
            shared = ""
        head_line = block.strip().splitlines()[0] if block.strip() else ""
        hc = wave_head_count(head_line)
        if isinstance(hc, int) and hc > 1 and 0 < len(items) < hc:
            items = [body.strip()]
            shared = ""
        nodes = [make_node(it, shared, preamble_domains) for it in items]
        if nodes:
            waves.append((int(h.group(1)), nodes, hc))

    if not waves:
        for wn, nodes, dn in parse_old_dispatch(seg, preamble_domains):
            waves.append((wn, nodes, dn))

    # 散文式 wave（仅当该 wave 编号无编号头时补入）
    have = {wn for wn, _, _ in waves}
    for pw in parse_prose_waves(preamble, preamble_domains):
        if pw["wave_num"] not in have:
            waves.append((pw["wave_num"], pw["nodes"], None))
            have.add(pw["wave_num"])

    waves.sort(key=lambda x: x[0])
    out = []
    for wn, nodes, dn in waves:
        dyn = (dn == "dynamic")
        n_agents = dn if isinstance(dn, int) else None
        if n_agents is None:
            nas = [n.get("n_agents") for n in nodes if n.get("n_agents")]
            n_agents = sum(nas) if nas else len(nodes)
        w = {"wave_id": "wave_%d" % wn, "nodes": nodes, "n_agents": n_agents}
        if dyn:
            w["n_agents_dynamic"] = True
        out.append(w)
    return out


