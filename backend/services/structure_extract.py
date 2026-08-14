"""规则引擎：从文本提取文档结构 —— 0 次 LLM 调用。

移植自 agent-quiz-feature/server/src/lib/extract-structure.ts（导入 Agent 配套）。
格式层（标题/粗体/列表）全语言通用；语义层（定义/对比/别称）按语言选正则集。
中文/英文走规则，其他语言由 LLM 兜底。
"""
import re
from dataclasses import dataclass, field

# ── 数据结构 ────────────────────────────────────────────────────────────


@dataclass
class Heading:
    level: int
    text: str
    line: int


@dataclass
class TermRef:
    term: str
    line: int


@dataclass
class DefPair:
    term: str
    definition: str
    line: int


@dataclass
class ContrastPair:
    term_a: str
    term_b: str
    dimension: str
    line: int


@dataclass
class ListItem:
    item: str
    line: int
    context: str


@dataclass
class StructureResult:
    language: str  # "zh" | "en" | "other"
    title: str = ""
    headings: list[Heading] = field(default_factory=list)
    terms: list[TermRef] = field(default_factory=list)
    definitions: list[DefPair] = field(default_factory=list)
    contrast_pairs: list[ContrastPair] = field(default_factory=list)
    list_items: list[ListItem] = field(default_factory=list)
    total_lines: int = 0


@dataclass
class TextChunk:
    text: str
    start_line: int
    end_line: int
    index: int


# ── 语言检测 ────────────────────────────────────────────────────────────

# 英语高频停用词——非英语的拉丁字母语言（法语/德语/西班牙语）命中率极低
_EN_STOPWORDS = re.compile(
    r"\b(the|of|and|is|are|was|were|to|in|that|it|for|with|as|on|by|be|this|which|or|an"
    r"|at|from|not|but|have|has|had|do|does|can|could|would|should|will|may|if|then|than"
    r"|so|we|you|they|he|she)\b",
    re.IGNORECASE,
)


def detect_language(content: str) -> str:
    total = len(content)
    if total == 0:
        return "other"
    cjk = len(re.findall(r"[一-鿿぀-ヿ가-힯]", content))
    if cjk > total * 0.05:
        return "zh"
    latin = len(re.findall(r"[a-zA-Z]", content))
    if latin > total * 0.5:
        # 用停用词密度区分英语和其他拉丁字母语言
        stopword_hits = len(_EN_STOPWORDS.findall(content))
        return "en" if stopword_hits > latin * 0.02 else "other"
    return "other"


# ── 各语言模式集 ────────────────────────────────────────────────────────


@dataclass
class LangPatterns:
    heading_patterns: list[re.Pattern]
    def_patterns: list[re.Pattern]
    contrast_patterns: list[re.Pattern]
    list_intro_re: re.Pattern | None
    skip_prefixes: re.Pattern


_ZH = LangPatterns(
    heading_patterns=[
        re.compile(r"^第[一二三四五六七八九十百千0-9]+[章][：:\s]*(.*)$"),
        re.compile(r"^第[一二三四五六七八九十百千0-9]+[节][：:\s]*(.*)$"),
        re.compile(r"^[一二三四五六七八九十]+[、.．]\s*(.+)$"),
    ],
    def_patterns=[
        re.compile(r"^(.{2,40}?)(?:指的是|定义为|是指|即|是)\s*(.{2,})$"),  # 谓词
        re.compile(r"^(.{2,40}?)[：:]\s*(.{2,})$"),  # 同位
        re.compile(r"^(.{2,40}?)(?:又称|也叫|亦称|又叫|也称)\s*(.{2,40})$"),  # 别称
        re.compile(r"^(.{2,40}?)\s*[—\-]{2,}\s*(.{2,})$"),  # 破折
    ],
    contrast_patterns=[
        re.compile(r"(.{2,40})(?:不同于|区别于|有别于)(.{2,40})"),
        re.compile(r"(.{2,40}?)(?:与|和|跟|同)(.{2,40}?)(?:的区别|的不同|的差异|相比|对比|比较|不同|的异同)"),
        re.compile(r"(?:相比于|相对于|相较|相较于)(.{2,40})[，,]\s*(.{2,40})"),
    ],
    list_intro_re=re.compile(
        r"(?:分为|包括|包含|有以下|有如下|以下几种|有如下几种|以下几[点方面类]|如下几[点方面类])[：:]?\s*$"
    ),
    skip_prefixes=re.compile(
        r"^(?:但是|然而|无论|如果|因为|所以|虽然|而且|并且|因此|于是|然后|接着|最后|首先"
        r"|其次|另外|此外|总之|比如|例如|假如|假设|比方说|说到底|换句话|简单[说来]"
        r"|毫无[疑问]|注意|提示|备注|其中|另外|由于|之后|以后|随后|同时|下面|以下"
        r"|目前|现在|基本|通常|一般)"
    ),
)

_EN = LangPatterns(
    heading_patterns=[
        re.compile(r"^(?:Chapter|CHAPTER)\s+(\d+|[IVXLCDM]+)[.:\s]*(.*)$"),
        re.compile(r"^(?:Section|SECTION)\s+(\d+(?:\.\d+)*)[.:\s]*(.*)$"),
        re.compile(r"^(\d+(?:\.\d+)+)[\s.]+(.+)$"),
    ],
    def_patterns=[
        re.compile(
            r"^(.{2,60}?)\s+(?:is|are|refers to|is defined as|means|denotes)\s+(.{2,})$",
            re.IGNORECASE,
        ),
        re.compile(r"^(.{2,60}?):\s*(.{2,})$"),  # colon
        re.compile(
            r"^(.{2,60}?)\s+(?:aka|also called|also known as|a\.k\.a\.?)\s+(.{2,60})$",
            re.IGNORECASE,
        ),
        re.compile(r"^(.{2,60}?)\s*[—\-]{2,}\s*(.{2,})$"),  # em-dash
    ],
    contrast_patterns=[
        re.compile(r"(.{2,60}?)\s+(?:vs\.?|versus)\s+(.{2,60})", re.IGNORECASE),
        re.compile(r"(.{2,60}?)\s+differs?\s+from\s+(.{2,60})", re.IGNORECASE),
        re.compile(
            r"(?:difference|distinction)\s+between\s+(.{2,60}?)\s+and\s+(.{2,60})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(.{2,60}?)\s+(?:compared to|compared with|in contrast to)\s+(.{2,60})",
            re.IGNORECASE,
        ),
    ],
    list_intro_re=re.compile(
        r"(?:includes?|contains?|consists? of|as follows|the following)[:]?\s*$",
        re.IGNORECASE,
    ),
    skip_prefixes=re.compile(
        r"^(?:However|Nevertheless|Because|Since|If|Although|Therefore|Thus|Then|Finally"
        r"|First|Secondly|Next|Besides|Moreover|In addition|For example|For instance"
        r"|Note that|Notice|Currently|Generally|Usually|In summary|To sum up|As a result"
        r"|On the other hand|In other words)[\s,.]",
        re.IGNORECASE,
    ),
)

_OTHER = LangPatterns(
    heading_patterns=[],
    def_patterns=[],
    contrast_patterns=[],
    # 语言无关的列表引导：以冒号结尾的行 + 后续列表项
    list_intro_re=re.compile(r"^.{2,80}[：:]\s*$"),
    skip_prefixes=re.compile(r"(?!)"),  # 不跳过任何行
)

# 语言无关的格式层模式
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(^|[^*\s])\*([^*\n]{2,60})\*(?!\*)")
_BRACKET_RE = re.compile(r"[「『]([^」』]{2,40})[」』]")
_LIST_ITEM_RE = re.compile(r"^[-*•·]\s+(.+)$|^(\d+)[.、)）]\s*(.+)$|^[（(](\d+)[）)]\s*(.+)$")

_SHORT_WORD_RE = re.compile(r"^[a-z]{1,3}$", re.IGNORECASE)
_PUNCT_ONLY_RE = re.compile(r"^[，。、；：！？]$")
_TERM_CLEAN_RE = re.compile(r"[，。、；：,.;:]+\s*$")
_BAD_DEF_TERM_RE = re.compile(r"(?:是否|要不要|能不能|可不可以)")
_BAD_DEF_SUFFIX_RE = re.compile(
    r"(?:但是|然而|如果|因为|所以|虽然|注意|提示|由于|之后|以后|目前|现在)$"
)


def extract_structure_from_text(content: str) -> StructureResult:
    lines = content.split("\n")
    lang = detect_language(content)
    patterns = _ZH if lang == "zh" else _EN if lang == "en" else _OTHER

    headings: list[Heading] = []
    terms: list[TermRef] = []
    definitions: list[DefPair] = []
    contrast_pairs: list[ContrastPair] = []
    list_items: list[ListItem] = []
    title = ""

    i = 0
    while i < len(lines):
        line = lines[i]

        # ── Markdown 标题（全语言通用）──
        hm = _HEADING_RE.match(line)
        if hm:
            level = len(hm.group(1))
            headings.append(Heading(level=level, text=hm.group(2).strip(), line=i + 1))
            if level == 1 and not title:
                title = hm.group(2).strip()
            i += 1
            continue

        # ── 语言相关标题 ──
        heading_matched = False
        for idx, pattern in enumerate(patterns.heading_patterns):
            if pattern.match(line):
                level = 1 if idx == 0 else 2 if idx == 1 else 3
                headings.append(Heading(level=level, text=line.strip(), line=i + 1))
                if level == 1 and not title:
                    title = line.strip()
                heading_matched = True
                break
        if heading_matched:
            i += 1
            continue

        # ── 粗体术语（全语言通用）──
        for bm in _BOLD_RE.finditer(line):
            t = bm.group(1).strip()
            if 2 <= len(t) < 60 and "*" not in t and not _SHORT_WORD_RE.match(t):
                terms.append(TermRef(term=t, line=i + 1))

        # ── 斜体术语（英文常见）──
        for im in _ITALIC_RE.finditer(line):
            t = im.group(2).strip()
            if 2 <= len(t) < 60:
                terms.append(TermRef(term=t, line=i + 1))

        # ── 「」括号术语 ──
        for brm in _BRACKET_RE.finditer(line):
            t = brm.group(1).strip()
            if not _PUNCT_ONLY_RE.match(t):
                terms.append(TermRef(term=t, line=i + 1))

        # ── 列举引导句 + 列表项收集（引导句语言相关，列表项语言无关）──
        if patterns.list_intro_re and patterns.list_intro_re.search(line):
            context = line.strip()
            j = i + 1
            while j < len(lines) and j < i + 30:
                item_line = lines[j].strip()
                if not item_line:
                    break
                if _HEADING_RE.match(item_line):
                    break
                lm = _LIST_ITEM_RE.match(item_line)
                if lm:
                    # 取条目文本组（1=符号列表 3=数字列表 5=（数字）列表）；
                    # 注：原 TS 实现误取数字组（2/4）导致编号条目被长度过滤丢弃，此处修正
                    item = (lm.group(1) or lm.group(3) or lm.group(5) or "").strip()
                    if 2 <= len(item) < 100:
                        list_items.append(ListItem(item=item, line=j + 1, context=context))
                    j += 1
                    continue
                break
            i = j
            continue

        # ── 语义层（仅中英文走规则）──
        if lang != "other" and 5 <= len(line) <= 300 and not patterns.skip_prefixes.match(line):
            if not patterns.list_intro_re or not patterns.list_intro_re.search(line):
                for pattern in patterns.def_patterns:
                    dm = pattern.match(line)
                    if dm:
                        t = _TERM_CLEAN_RE.sub(
                            "", dm.group(1).replace("**", "").replace("「", "")
                            .replace("」", "").replace("『", "").replace("』", "")
                        ).strip()
                        d = dm.group(2).strip()
                        if (
                            1 < len(t) < 60
                            and len(d) > 1
                            and not _BAD_DEF_TERM_RE.search(t)
                            and not _BAD_DEF_SUFFIX_RE.search(t)
                        ):
                            definitions.append(DefPair(term=t, definition=d, line=i + 1))
                        break

            for pattern in patterns.contrast_patterns:
                cm = pattern.search(line)
                if cm:
                    matched_text = cm.group(0)
                    dimension = (
                        "区别"
                        if re.search(r"区别|differs|difference", matched_text)
                        else "对比"
                    )
                    contrast_pairs.append(
                        ContrastPair(
                            term_a=cm.group(1).strip(),
                            term_b=cm.group(2).strip(),
                            dimension=dimension,
                            line=i + 1,
                        )
                    )
                    break

        i += 1

    # 去重：定义保留最长释义，术语保留首次出现行号
    def_map: dict[str, DefPair] = {}
    for d in definitions:
        existing = def_map.get(d.term)
        if existing is None or len(d.definition) > len(existing.definition):
            def_map[d.term] = d

    term_map: dict[str, int] = {}
    for t in terms:
        if t.term not in term_map:
            term_map[t.term] = t.line

    return StructureResult(
        language=lang,
        title=title,
        headings=headings,
        terms=[TermRef(term=term, line=line) for term, line in term_map.items()],
        definitions=list(def_map.values()),
        contrast_pairs=contrast_pairs,
        list_items=list_items,
        total_lines=len(lines),
    )


# ── 知识点生成（纯规则） ────────────────────────────────────────────────


def build_knowledge_from_structure(structure: StructureResult, file_name: str) -> dict:
    """由规则结构产出知识 dict：{title, fileName, chapters: [...]}。

    chapters 元素：{chapter_id, title, content, knowledge_points}；
    knowledge_points 元素：{id, name, importance, difficulty}（importance/difficulty 仅供
    决策参考，入库时丢弃——Knowledge 表无这两列）。
    """
    chapters: list[dict] = []

    def push_chapter(title: str) -> None:
        chapters.append(
            {
                "chapter_id": f"ch_{len(chapters) + 1:02d}",
                "title": title,
                "content": "",
                "knowledge_points": [],
            }
        )

    if not structure.headings:
        push_chapter("全文")
    for h in structure.headings:
        if h.level <= 2:
            push_chapter(h.text)
    if not chapters:
        push_chapter(structure.title or "未分类")

    kp_id = 0

    def add_point(ch: dict | None, name: str, importance: int, difficulty: int) -> None:
        nonlocal kp_id
        if not ch:
            return
        if any(kp["name"] == name for kp in ch["knowledge_points"]):
            return
        kp_id += 1
        ch["knowledge_points"].append(
            {
                "id": f"kp_{kp_id:03d}",
                "name": name,
                "importance": importance,
                "difficulty": difficulty,
            }
        )

    for d in structure.definitions:
        ch = _find_chapter_for_line(d.line, structure.headings, chapters)
        if not ch:
            continue
        importance = _estimate_importance(d.term, structure)
        add_point(ch, d.term, importance, 3 if len(d.definition) > 40 else 2)
        pair = f"{d.term}：{d.definition}"
        ch["content"] = f"{ch['content']}；{pair}" if ch["content"] else pair

    for c in structure.contrast_pairs:
        ch = _find_chapter_for_line(c.line, structure.headings, chapters)
        if not ch:
            continue
        add_point(ch, c.term_a, 4, 4)
        add_point(ch, c.term_b, 4, 4)

    for li in structure.list_items:
        ch = _find_chapter_for_line(li.line, structure.headings, chapters)
        if not ch:
            continue
        name = li.item[:40] + "…" if len(li.item) > 40 else li.item
        add_point(ch, name, 3, 2)

    defined_terms = {d.term for d in structure.definitions}
    for t in structure.terms:
        if t.term in defined_terms:
            continue
        ch = _find_chapter_for_line(t.line, structure.headings, chapters) or (
            chapters[0] if chapters else None
        )
        add_point(ch, t.term, _estimate_importance(t.term, structure), 2)

    return {
        "title": structure.title or file_name or "未命名文档",
        "fileName": file_name,
        "chapters": [ch for ch in chapters if ch["knowledge_points"]],
    }


# ── 辅助 ────────────────────────────────────────────────────────────────


def _find_chapter_for_line(line: int, headings: list[Heading], chapters: list[dict]) -> dict | None:
    cur: Heading | None = None
    for h in headings:
        if h.line > line:
            break
        if h.level <= 2:
            cur = h
    if cur is None:
        return chapters[0] if chapters else None
    for ch in chapters:
        if ch["title"] == cur.text:
            return ch
    return chapters[0] if chapters else None


def _estimate_importance(term: str, s: StructureResult) -> int:
    if any(term in h.text for h in s.headings):
        return 5
    dc = sum(1 for d in s.definitions if d.term == term or term in d.definition)
    if dc >= 3:
        return 5
    if dc >= 2:
        return 4
    if any(term in c.term_a or term in c.term_b for c in s.contrast_pairs):
        return 4
    return 3


# ── 分块与匹配（供交叉验证使用） ────────────────────────────────────────


def pick_chunk_size(text_length: int) -> int:
    """动态块大小：目标约 40 块，钳制在 600-2000 字符。"""
    if text_length == 0:
        return 600
    target = -(-text_length // 40)  # ceil
    return min(2000, max(600, target))


def split_text_with_lines(text: str, chunk_size: int) -> list[TextChunk]:
    """段落级分块，保留行号（章节映射必需）。"""
    lines = text.split("\n")
    chunks: list[TextChunk] = []
    cur_text = ""
    cur_start = 1
    i = 0

    while i < len(lines):
        # 跳到下一个非空行（段落起点）
        while i < len(lines) and lines[i].strip() == "":
            i += 1
        if i >= len(lines):
            break
        para_start = i

        # 找到段落结束（空行）
        j = i
        while j < len(lines) and lines[j].strip() != "":
            j += 1
        para = "\n".join(lines[i:j])

        if cur_text and len(cur_text) + len(para) + 2 > chunk_size:
            chunks.append(
                TextChunk(
                    text=cur_text.strip(),
                    start_line=cur_start,
                    end_line=para_start,
                    index=len(chunks),
                )
            )
            cur_text = para
            cur_start = para_start + 1
        else:
            cur_text = f"{cur_text}\n\n{para}" if cur_text else para
        i = j

    if cur_text.strip():
        chunks.append(
            TextChunk(
                text=cur_text.strip(),
                start_line=cur_start,
                end_line=len(lines),
                index=len(chunks),
            )
        )
    return chunks


_NORMALIZE_STRIP_RE = re.compile(r"[，。、；：！？「」『』（）()【】《》\"'“”‘’.,;:!?\-—–\[\]{}<>]")
_ARTICLE_RE = re.compile(r"^(?:the|a|an)(?=\S)", re.IGNORECASE)


def normalize_term(term: str) -> str:
    """归一化术语：小写、去空白、去标点、去英文冠词。"""
    t = term.lower()
    t = re.sub(r"[\s　]+", "", t)
    t = _NORMALIZE_STRIP_RE.sub("", t)
    t = _ARTICLE_RE.sub("", t)
    return t


def terms_match(a: str, b: str) -> bool:
    """匹配：归一化后相等或相互包含。"""
    na, nb = normalize_term(a), normalize_term(b)
    if not na or not nb or len(na) < 2 or len(nb) < 2:
        return False
    return na == nb or na in nb or nb in na


def compute_match_stats(llm_kps: list[dict], rule_kps: list[dict]) -> dict:
    """计算 recall 与 precision：llmKps vs ruleKps（元素含 name 字段）。"""
    if not llm_kps or not rule_kps:
        return {"recall": 0, "precision": 0, "matched": 0}
    matched = sum(
        1 for lk in llm_kps if any(terms_match(lk["name"], rk["name"]) for rk in rule_kps)
    )
    recall = matched / len(llm_kps)
    # precision：规则知识点被 LLM 确认的比例
    confirmed = sum(
        1 for rk in rule_kps if any(terms_match(lk["name"], rk["name"]) for lk in llm_kps)
    )
    precision = confirmed / len(rule_kps)
    return {"recall": recall, "precision": precision, "matched": matched}
