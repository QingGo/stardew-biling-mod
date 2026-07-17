"""
Text parsers for Stardew Valley bilingual content pack generation.

Handles:
  - Dialogue #$b#/#$e# segmentation + $d/$p conditionals
  - Mail [#] markers + command dedup
  - Event script /-split + $q/$r inline Q&A
  - $y quick question format
  - TV CookingChannel recipe prefix
"""

import re
from typing import Optional

BILINGUAL_TEMPLATE = "{left} / {right}"

# ====== Shared ======

SEGMENT_RE = re.compile(r'(#\$[eb]#)')
D1_SEGMENT_RE = re.compile(r'^(#\$1\s+\S+#)(.*)')
D_COND_RE = re.compile(r'^(\$d\s+\w+#)(.*?)\|(.*)$')
EMOTION_RE = re.compile(r'(\$\w+)\s*$')
Y_Q_RE = re.compile(r"^\$y\s*'(.*)'$", re.DOTALL)
DIALOGUE_Q_RE = re.compile(r'(#?\$q\s+[^#]*#)(.*)', re.DOTALL)
DIALOGUE_R_RE = re.compile(r'#\$r\s+([^#]+)#(.*?)(?=#\$r|#\$q|#\$e|#\$b|$)', re.DOTALL)


def _find_first_caret_outside_token(text: str) -> int:
    """Find the first ^ outside ${...}$ CP tokens.
    Returns index, or -1 if none."""
    depth = 0
    i = 0
    while i < len(text):
        if text[i] == '$' and i + 1 < len(text) and text[i+1] == '{':
            depth += 1
            i += 2
        elif text[i] == '}':
            depth -= 1
            if depth < 0:
                depth = 0
            i += 1
        elif text[i] == '^' and depth == 0:
            return i
        else:
            i += 1
    return -1


def _bilingualize_y_text(en_val: str, zh_val: str) -> Optional[str]:
    """Handle $y 'Question_Opt1_Resp1_...' quick question format.
    
    Splits content by _ to pair question/option/response segments
    between EN and ZH. Each segment is independently bilingualized
    via bilingualize_pair, preserving any nested #$b# or ^ markers.
    
    Returns bilingual string or None if format doesn't match.
    """
    en_m = Y_Q_RE.match(en_val)
    zh_m = Y_Q_RE.match(zh_val)

    if not en_m or not zh_m:
        return None

    en_segments = en_m.group(1).split('_')
    zh_segments = zh_m.group(1).split('_')

    if len(en_segments) != len(zh_segments):
        return None

    bi_segments = [bilingualize_pair(es, zs) for es, zs in zip(en_segments, zh_segments)]

    return "$y '" + '_'.join(bi_segments) + "'"


_qr_depth = 0


def _bilingualize_dialogue_qr(en_text: str, zh_text: str) -> Optional[str]:
    """Handle dialogue $q/$r Q&A format.

    Both event ($q) and dialogue (#$q) patterns are supported.
    Preserves EN command structure, bilingualizes only the text portions.

    Input EN:  ...text $q -1 -1#question?#$r -1 -1 Yes#yes.#$r -1 -1 No#no.
    Input ZH:  ...text $q -1 -1#问题？#$r -1 -1 Yes#是。#$r -1 -1 No#不。
    Output:    ...text / ...text $q -1 -1#question? / 问题？#$r -1 -1 Yes#yes. / 是。#$r -1 -1 No#no. / 不。
    """
    global _qr_depth
    if _qr_depth > 0:
        return None
    if '$q' not in en_text or '$q' not in zh_text:
        return None

    en_q = DIALOGUE_Q_RE.search(en_text)
    zh_q = DIALOGUE_Q_RE.search(zh_text)

    if not en_q or not zh_q:
        return None
    
    _qr_depth += 1
    try:
        en_preamble = en_text[:en_q.start()]
        zh_preamble = zh_text[:zh_q.start()]
        preamble_bi = bilingualize_pair(en_preamble, zh_preamble) if en_preamble or zh_preamble else ""

        q_prefix = en_q.group(1)
        en_content = en_q.group(2)
        zh_content = zh_q.group(2)

        en_r_matches = list(DIALOGUE_R_RE.finditer(en_content))
        zh_r_matches = list(DIALOGUE_R_RE.finditer(zh_content))

        if not en_r_matches or not zh_r_matches:
            q_bi = bilingualize_pair(en_content, zh_content)
            return f"{preamble_bi}{q_prefix}{q_bi}"

        if len(en_r_matches) != len(zh_r_matches):
            return None

        en_q_text = en_content[:en_r_matches[0].start()]
        zh_q_text = zh_content[:zh_r_matches[0].start()]
        q_bi = bilingualize_pair(en_q_text, zh_q_text) if en_q_text or zh_q_text else ""

        en_last_end = en_r_matches[-1].end()
        zh_last_end = zh_r_matches[-1].end()
        en_tail = en_content[en_last_end:]
        zh_tail = zh_content[zh_last_end:]
        tail_bi = bilingualize_pair(en_tail, zh_tail) if en_tail or zh_tail else ""

        responses = []
        for en_m, zh_m in zip(en_r_matches, zh_r_matches):
            en_args = en_m.group(1)
            en_resp = en_m.group(2)
            zh_resp = zh_m.group(2)
            resp_bi = bilingualize_pair(en_resp, zh_resp)
            responses.append(f"#$r {en_args}#{resp_bi}")

        return f"{preamble_bi}{q_prefix}{q_bi}{''.join(responses)}{tail_bi}"
    finally:
        _qr_depth -= 1


def bilingualize_pair(en_val: str, zh_val: str) -> str:
    """Bilingualize a single text pair, handling ^ gender split, $y quick questions,
    and $q/$r dialogue Q&A.

    Game engine processes ^ before #$b#, so ^ must pair EN/zh branches
    correctly: \"EN_male / ZH_male ^ EN_female / ZH_female\"

    $y 'Question_Opt1_Resp1_...' format is detected and handled
    by pairing question/option/response segments between languages.

    $q/$r dialogue Q&A format is detected and handled by preserving
    the EN command structure and bilingualizing only the text portions.
    """
    # Handle $q/$r dialogue Q&A — must be before ^ check since $q uses #
    if '$q' in en_val and '$q' in zh_val:
        qr_result = _bilingualize_dialogue_qr(en_val, zh_val)
        if qr_result is not None:
            return qr_result

    # Handle $y quick question format — must be before ^ check
    # since $y uses _ as delimiter, not ^
    if '$y' in en_val and '$y' in zh_val:
        y_result = _bilingualize_y_text(en_val, zh_val)
        if y_result is not None:
            return y_result

    en_idx = _find_first_caret_outside_token(en_val)
    zh_idx = _find_first_caret_outside_token(zh_val)

    has_en_caret = en_idx >= 0
    has_zh_caret = zh_idx >= 0

    if not has_en_caret and not has_zh_caret:
        return BILINGUAL_TEMPLATE.format(left=en_val, right=zh_val)

    en_left = en_val[:en_idx] if has_en_caret else en_val
    en_right = en_val[en_idx+1:] if has_en_caret else en_val
    zh_left = zh_val[:zh_idx] if has_zh_caret else zh_val
    zh_right = zh_val[zh_idx+1:] if has_zh_caret else zh_val

    left = BILINGUAL_TEMPLATE.format(left=en_left, right=zh_left)
    right = BILINGUAL_TEMPLATE.format(left=en_right, right=zh_right)
    return f"{left}^{right}"


def _bilingualize_d1_segment(en_val: str, zh_val: str) -> Optional[str]:
    """对 #$1 条件对话段做双语，将中文插入 $k 终结符之前。

    输入:  #$1 cond#EN_TEXT$TERM[AFTER]
           #$1 cond#ZH_TEXT$TERM[AFTER]
    输出:  #$1 cond#EN_TEXT / ZH_TEXT$TERM[AFTER]

    TERM 为 $k 或 $0。若无 $k/$0（以 #$e#/#$b# 或段尾终结），
    则视整段为条件文本段做双语，仅保留 EN 前缀。
    """
    en_m = D1_SEGMENT_RE.match(en_val)
    zh_m = D1_SEGMENT_RE.match(zh_val)
    if not en_m or not zh_m:
        return None

    prefix = en_m.group(1)
    en_inner = en_m.group(2)
    zh_inner = zh_m.group(2)

    en_term = re.search(r'\$[0k]', en_inner)
    if not en_term:
        en_block = en_inner
        terminator = ""
        en_after = ""
        zh_block = zh_inner
    else:
        en_block = en_inner[:en_term.start()]
        terminator = en_term.group(0)
        en_after = en_inner[en_term.end():]
        zh_term_idx = zh_inner.find(terminator)
        if zh_term_idx < 0:
            return None
        zh_block = zh_inner[:zh_term_idx]
        zh_after = zh_inner[zh_term_idx + len(terminator):]

    bi_block = bilingualize_pair(en_block, zh_block)
    return f"{prefix}{bi_block}{terminator}{en_after}"


def _bilingualize_segments(en_val: str, zh_val: str) -> str:
    """按 #$e# / #$b# 分段后做双语，每段独立拼接。"""
    en_parts = SEGMENT_RE.split(en_val)
    zh_parts = SEGMENT_RE.split(zh_val)

    if len(en_parts) != len(zh_parts):
        return bilingualize_pair(en_val, zh_val)

    result = []
    for en_part, zh_part in zip(en_parts, zh_parts):
        if en_part in ('#$e#', '#$b#'):
            result.append(en_part)
        elif en_part and zh_part:
            d1 = _bilingualize_d1_segment(en_part, zh_part)
            if d1 is not None:
                result.append(d1)
            else:
                en_d1 = D1_SEGMENT_RE.match(en_part)
                zh_d1 = D1_SEGMENT_RE.match(zh_part)
                if en_d1 and zh_d1:
                    prefix = en_d1.group(1)
                    bi_text = bilingualize_pair(en_d1.group(2), zh_d1.group(2))
                    result.append(f"{prefix}{bi_text}")
                else:
                    result.append(bilingualize_pair(en_part, zh_part))
        elif en_part:
            result.append(f"{en_part} / ")
        elif zh_part:
            result.append(f" / {zh_part}")
    return "".join(result)


# ====== Layer 3: Dialogue with $d conditionals ======

def make_dialogue_bilingual(en_val: str, zh_val: str) -> str:
    """对对话条目做双语。

    1. 如果值为 $d COND#true|false 格式，按分支双语再拼接
    2. 否则按 #$e#/#$b# 分段双语
    """
    d_en = D_COND_RE.match(en_val)
    d_zh = D_COND_RE.match(zh_val)

    if d_en and d_zh:
        prefix = d_en.group(1)
        true_en = d_en.group(2)
        false_en = d_en.group(3)
        true_zh = d_zh.group(2)
        false_zh = d_zh.group(3)

        # 提取尾部情绪代码（仅保留一组）
        em_en = EMOTION_RE.search(false_en)
        em_zh = EMOTION_RE.search(false_zh)
        if em_en or em_zh:
            emotion = em_en.group(0) if em_en else em_zh.group(0)
            false_en = false_en[:em_en.start()].rstrip() if em_en else false_en.rstrip()
            false_zh = false_zh[:em_zh.start()].rstrip() if em_zh else false_zh.rstrip()
        else:
            emotion = ""

        true_bi = _bilingualize_segments(true_en, true_zh)
        false_bi = _bilingualize_segments(false_en, false_zh)
        return f"{prefix}{true_bi}|{false_bi}{emotion}"

    p_result = _bilingualize_p_conditional(en_val, zh_val)
    if p_result is not None:
        return p_result

    return _bilingualize_segments(en_val, zh_val)


def _bilingualize_p_conditional(text_en: str, text_zh: str):
    """对 $p ID#OPT1|OPT2|...|DEFAULT 多分支条件做双语。

    EN 和 ZH 结构完全一致（已验证），按 | 分割后逐分支双语再拼接。
    每个分支可能包含嵌套 $p，递归处理。
    """
    p_en = re.match(r'^(\$p\s+\d+#)(.*)', text_en)
    p_zh = re.match(r'^(\$p\s+\d+#)(.*)', text_zh)
    if not p_en or not p_zh:
        return None

    prefix = p_en.group(1)
    branches_en = p_en.group(2).split('|')
    branches_zh = p_zh.group(2).split('|')
    if len(branches_en) != len(branches_zh):
        return None

    bi_branches = []
    for br_en, br_zh in zip(branches_en, branches_zh):
        nested_p_en = re.match(r'^(\$p\s+\d+#)(.*)', br_en)
        nested_p_zh = re.match(r'^(\$p\s+\d+#)(.*)', br_zh)
        if nested_p_en and nested_p_zh:
            nested = _bilingualize_p_conditional(br_en, br_zh)
            if nested is not None:
                bi_branches.append(nested)
            else:
                bi_branches.append(br_en)
        else:
            bi_branches.append(_bilingualize_segments(br_en, br_zh))

    return f"{prefix}{'|'.join(bi_branches)}"


# ====== Layer 1: Mail ======

MAIL_TITLE_RE = re.compile(r'(%%?\[#\]|\[#\])(.*)$')
MAIL_CMD_RE = re.compile(r'%[a-z]+\b.*?(?=\^|%|\[|$)')


def make_mail_bilingual(en_val: str, zh_val: str) -> str:
    """对信件条目做双语。

    策略：只保留 EN 的 [#] 标记和命令（%item, %money 等），
    ZH 只取纯文本部分做双语拼接。
    """
    en_match = MAIL_TITLE_RE.search(en_val)
    if not en_match:
        return BILINGUAL_TEMPLATE.format(left=en_val, right=zh_val)

    en_marker = en_match.group(1)
    en_title = en_match.group(2)
    en_body = en_val[:en_match.start()]

    zh_match = MAIL_TITLE_RE.search(zh_val)
    if zh_match:
        zh_body = zh_val[:zh_match.start()]
        zh_title = zh_match.group(2)
    else:
        zh_body = zh_val
        zh_title = ""

    zh_body_clean = MAIL_CMD_RE.sub('', zh_body).strip()
    if not zh_body_clean:
        zh_body_clean = zh_body

    # 如果 EN body 末尾有 %command 且未以 %% 终结，补上终结符
    # 确保命令在 / 分隔符之前被关闭，不会被游戏解析器吞掉正文
    if '%' in en_body and not en_body.rstrip().endswith('%%'):
        en_body = en_body.rstrip() + ' %%'
        en_marker = re.sub(r'^%+', '', en_marker)

    body_bi = BILINGUAL_TEMPLATE.format(left=en_body, right=zh_body_clean)
    title_bi = BILINGUAL_TEMPLATE.format(left=en_title, right=zh_title) if zh_title else en_title
    return f"{body_bi} {en_marker}{title_bi}"


# ====== Layer 2: Event scripts ======

EVENT_TEXT_COMMANDS = ("speak ", "message ", "question ", "quickQuestion ", "textAboveHead ", "dialogue ")
QR_RE = re.compile(r'#\$r\s+([^#]+)#(.*?)(?=#\$r|$)')
Q_PREFIX_RE = re.compile(r'(\$q\s+[^#]*#)(.*)')


def split_event_script(script: str) -> list:
    """按 / 分割事件脚本，但尊重引号内的内容"""
    parts = []
    current = []
    in_quotes = False
    for c in script:
        if c == '"':
            in_quotes = not in_quotes
            current.append(c)
        elif c == '/' and not in_quotes:
            parts.append(''.join(current))
            current = []
        else:
            current.append(c)
    if current:
        parts.append(''.join(current))
    return parts


def get_quoted_text(cmd: str) -> str:
    """从命令中提取第一个引号内的文本"""
    start = cmd.find('"')
    if start < 0:
        return ""
    end = cmd.find('"', start + 1)
    if end < 0:
        return ""
    return cmd[start + 1:end]


def replace_quoted_text(cmd: str, new_text: str) -> str:
    """替换命令中第一个引号内的文本"""
    start = cmd.find('"')
    if start < 0:
        return cmd
    end = cmd.find('"', start + 1)
    if end < 0:
        return cmd
    return cmd[:start + 1] + new_text + cmd[end:]


def is_text_command(cmd: str) -> bool:
    """判断是否为包含对话文本的命令"""
    stripped = cmd.strip()
    return any(stripped.startswith(p) for p in EVENT_TEXT_COMMANDS)


def bilingualize_qr_text(en_text: str, zh_text: str) -> str:
    """对含 $q/$r 内联问答的文本做双语。

    策略：
    1. 解析 $q 前缀和问题文本
    2. 解析每个 #$r 响应的前缀和响应文本
    3. 每个文本片段独立双语（可含 #$b#）
    4. 用 EN 的命令前缀重建完整字符串
    """
    en_q = Q_PREFIX_RE.match(en_text)
    zh_q = Q_PREFIX_RE.match(zh_text)

    if not en_q or not zh_q:
        return _bilingualize_segments(en_text, zh_text)

    q_prefix = en_q.group(1)
    rest_en = en_q.group(2)
    rest_zh = zh_q.group(2)

    # 找到第一个 #$r 位置，分割问题文本和响应区
    en_r_idx = rest_en.find('#$r')
    zh_r_idx = rest_zh.find('#$r')

    q_en = rest_en[:en_r_idx] if en_r_idx >= 0 else rest_en
    q_zh = rest_zh[:zh_r_idx] if zh_r_idx >= 0 else rest_zh
    q_bi = _bilingualize_segments(q_en, q_zh)

    if en_r_idx < 0 or zh_r_idx < 0:
        return f"{q_prefix}{q_bi}"

    # 解析每个 #$r 响应
    r_en = rest_en[en_r_idx:]
    r_zh = rest_zh[zh_r_idx:]

    en_matches = list(QR_RE.finditer(r_en))
    zh_matches = list(QR_RE.finditer(r_zh))

    responses = []
    for en_m, zh_m in zip(en_matches, zh_matches):
        en_args = en_m.group(1)
        en_resp = en_m.group(2)
        zh_args = zh_m.group(1)
        zh_resp = zh_m.group(2)

        resp_bi = _bilingualize_segments(en_resp, zh_resp)
        responses.append(f"#$r {en_args}#{resp_bi}")

    return f"{q_prefix}{q_bi}{''.join(responses)}"


def bilingualize_event_quoted_text(en_text: str, zh_text: str) -> str:
    """对事件 speak/message 引号内文本做双语。

    - 含 $q: 使用 $q/$r 解析器
    - 含 $p: 使用 $p 条件分支双语器
    - 其他: 使用标准分段双语
    """
    if not en_text or not zh_text or en_text == zh_text:
        return en_text or zh_text

    if '$q' in en_text and '$q' in zh_text:
        en_q_idx = en_text.index('$q')
        zh_q_idx = zh_text.index('$q')

        pre_en = en_text[:en_q_idx]
        pre_zh = zh_text[:zh_q_idx]
        pre_bi = _bilingualize_segments(pre_en, pre_zh) if pre_en or pre_zh else ""

        q_en = en_text[en_q_idx:]
        q_zh = zh_text[zh_q_idx:]
        q_bi = bilingualize_qr_text(q_en, q_zh)

        return pre_bi + q_bi

    p_result = _bilingualize_p_conditional(en_text, zh_text)
    if p_result is not None:
        return p_result

    return _bilingualize_segments(en_text, zh_text)


def make_event_bilingual(en_script: str, zh_script: str) -> str:
    """对事件脚本做双语。

    对 speak/message 等文本命令：
    - 引号内文本用 bilingualize_event_quoted_text
    - 非文本命令保持 EN 原样

    结构不匹配时回退到中文（安全降级）。
    """
    en_parts = split_event_script(en_script)
    zh_parts = split_event_script(zh_script)

    if len(en_parts) != len(zh_parts):
        return zh_script

    result = []
    for en_cmd, zh_cmd in zip(en_parts, zh_parts):
        if is_text_command(en_cmd) and is_text_command(zh_cmd):
            en_text = get_quoted_text(en_cmd)
            zh_text = get_quoted_text(zh_cmd)
            if en_text and zh_text and en_text != zh_text:
                bi_text = bilingualize_event_quoted_text(en_text, zh_text)
                result.append(replace_quoted_text(en_cmd, bi_text))
            else:
                result.append(en_cmd)
        else:
            result.append(en_cmd)

    return "/".join(result)
