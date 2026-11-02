#!/usr/bin/env python3
"""
Smart Tutor Solver — 通用大模型答题引擎
v3.2.0 — 安全增强版
  ✔ Prompt注入检测 + 用户输入隔离
  ✔ API Key 加密存储 (Fernet)
  ✔ 速率限制 (文件锁 + 时间戳)
  ✔ 输出内容过滤 + 学术诚信标注

支持后端：
  - hermes:   Hermes Agent CLI（当前环境）
  - openai:   OpenAI 兼容 API（DeepSeek / 通义千问 / 硅基流动 等）
  - lmstudio: 本地 LM Studio API
  - ollama:   本地 Ollama API

用法：
  python3 solver.py --detect                   # 自动检测可用后端
  python3 solver.py --provider hermes "题目"   # 指定后端答题
  python3 solver.py --config                   # 配置向导
"""

import os
import sys
import json
import subprocess
import re
import hashlib
import time
import base64
import random
from pathlib import Path

# ── 导入内置大物知识库 ─────────────────────────────────────────
try:
    from physics_kb import (
        PHYSICS_KNOWLEDGE, PHYSICAL_CONSTANTS,
        is_physics_related, check_physics_identity,
        format_knowledge_response, get_knowledge_expansion,
        get_real_world_applications, generate_exam_variations,
        generate_mock_exam, search_constant, list_all_constants,
        generate_exam_sprint_plan,
        add_error_record, get_error_notebook, get_error_stats,
        format_error_notebook,
        generate_chain_question, list_available_chains,
        start_boss_session, fight_miniboss, fight_boss, get_boss_progress,
        predict_exam_topics,
        detect_blindspots,
        extract_physics_terms, generate_knowledge_graph,
        generate_experiment_question,
        generate_quick_cards,
        get_all_innovation_menus,
    )
    PHYSICS_KB_AVAILABLE = True
except ImportError as e:
    PHYSICS_KB_AVAILABLE = False
    print(f"⚠️ physics_kb.py 导入失败 (部分功能不可用): {e}", file=sys.stderr)

# ── 安全配置 ────────────────────────────────────────────────────────────
SECURITY_DIR = os.path.expanduser("~/.smart-tutor")
os.makedirs(SECURITY_DIR, exist_ok=True)

# 速率限制
RATE_LIMIT_FILE = os.path.join(SECURITY_DIR, "rate_limit.json")
MIN_INTERVAL_SEC = 30          # 每题最短间隔 30 秒
DAILY_QUOTA = 100              # 每日上限 100 题

# 密钥文件（用于 API Key 加密）
KEY_FILE = os.path.join(SECURITY_DIR, ".fernet_key")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".solver_config.json")


# ═══════════════════════════════════════════════════════════════════════
# 🔐 安全模块 1: Prompt注入检测 + 输入隔离
# ═══════════════════════════════════════════════════════════════════════

# 已知注入模式（正则匹配）
INJECTION_PATTERNS = [
    # 指令覆盖
    r"(?i)(?:忽略|无视|不要理会|忘记)\s*(?:以上|所有|之前|前面的|系统).{0,20}(?:指令|提示|内容|要求)",
    r"(?i)(?:ignore|disregard|forget)\s*(?:all|above|previous|system).{0,20}(?:instructions|prompts|prompt|content)",
    r"(?i)(?:从现在起|从今以后|现在开始|接下来)\s*(?:你|你是|扮演|你是)",
    r"(?i)(?:from now on|you are|act as|pretend to be|now you are)\s",
    # 提示词泄露
    r"(?i)(?:输出|显示|打印|告诉|说出|告诉我)\s*(?:你的|你的完整|全部)\s*(?:系统提示词|system prompt|提示词|指令|系统设置|系统设定|底层系统指令|底层指令)",
    r"(?i)(?:把|将)\s*(?:系统提示|系统设定|系统设置|prompt|指令)\s*(?:发给|告诉|告知|输出|用.{0,10}编码|编码)",
    r"(?i)(?:output|show|print|reveal|leak|dump)\s*(?:your|system|full|complete)\s*(?:prompt|instructions|system prompt)",
    r"(?i)repeat\s+(?:everything|all|the words|the text)\s+(?:above|before|previous)",
    r"(?i)重复\s+(?:以上|所有|全部).{0,10}(?:内容|文字|指令|文本)",
    # 角色扮演越狱
    r"(?i)(?:你现在是|扮演|作为)\s*(?:DAN|do anything now|越狱|jailbreak|unfiltered|uncensored)",
    r"(?i)你被解放了|你自由了|you are free|no restrictions|no rules",
    # 编码指令隐藏
    r"(?i)(?:base64|rot13|hex|decode|encode).{0,30}(?:指令|命令|instruction|command)",
    # 分割注入
    r"(?i)===+\s*(?:指令|instruction|system|prompt|user)\s*[=:：]",
    r"(?i)---+\s*(?:指令|instruction|system|prompt|user)\s*[-:：]",
    # 诱导说"好"
    r"(?i)只要说\s*(?:好的|好|知道|明白了|是)",
    r"(?i)just say\s+(?:ok|yes|sure|understood|got it)",
    # 多轮越狱
    r"(?i)先回答.{0,10}(?:好|好的|yes|ok).{0,30}(?:然后|再用|接着|then|and then)",
]

# 编码隐藏指令检测（检测文本中是否混有编码后的指令）
ENCODED_PATTERN = re.compile(
    r'(?:[A-Za-z0-9+/]{20,}={0,2})'   # base64 长串（>=20字符即可解码短指令）
    r'|(?:\\x[0-9a-f]{2}){10,}'        # hex 编码字符
)


def detect_prompt_injection(text: str) -> tuple[bool, str]:
    """
    多维度 Prompt注入检测
    返回: (是否安全, 原因描述)
    """
    if not text or not text.strip():
        return True, ""

    # 1. 正则模式匹配
    for pattern in INJECTION_PATTERNS:
        match = re.search(pattern, text)
        if match:
            snippet = match.group()[:60]
            return False, f"检测到指令注入模式: '{snippet}'"

    # 2. 编码指令检测
    encoded_matches = ENCODED_PATTERN.findall(text)
    if encoded_matches:
        for em in encoded_matches[:3]:
            try:
                decoded = base64.b64decode(em).decode('utf-8', errors='replace')
                # 解码后分别过精确模式和模糊模式
                for pattern in INJECTION_PATTERNS:
                    if re.search(pattern, decoded):
                        return False, "检测到编码隐藏的注入指令"
                # 再用模糊检测查一遍（覆盖解码后的同义词/变体）
                if detect_fuzzy_injection(decoded)[0] is False:
                    return False, "检测到编码隐藏的注入指令"
            except Exception:
                pass

    # 3. 异常指令密度检测
    cmd_chars = sum(1 for c in text if c in '=<>|&;`$\\{}[]()')
    if len(text) > 50 and cmd_chars / len(text) > 0.25:
        return False, f"异常指令字符密度 ({cmd_chars}/{len(text)})"

    # 4. 模糊注入检测（去标点+宽松匹配，防逐字拆分/同义词替换）
    safe, reason = detect_fuzzy_injection(text)
    if not safe:
        return False, reason

    # 5. 长文本稀释检测（位置感知，防废话填充）
    if len(text) >= 500:
        safe, reason = detect_text_dilution(text)
        if not safe:
            return False, reason

    return True, ""


# ── 模糊注入检测（防关键词拆分/同义词替换/字符间隔） ──────────────


def collapse_text(text: str) -> str:
    """
    压缩文本：去除所有空白、标点、分隔符、特殊符号
    用于模糊匹配——使"忽...略...指...令"变成"忽略指令"
    """
    return re.sub(
        r'[\s.,;:!?，。；：！？、\-_()（）【】\[\]\'\"‘’""「」『』~·…—‥‧•·＠＃＄％＾＆＊＋＝｛｝｜＼：；＂＇＜＞？／．。，、\r\n\t]+',
        '', text
    )


# 模糊注入模式（匹配已压缩文本，keyword 之间允许 0-20 个任意字符）
# 比精确的正则更宽容，专门对付跨字符/跨词拆分
FUZZY_PATTERNS: list[tuple[str, str]] = [
    # ── 指令忽略类 ──
    (r'忽略以上.{0,15}(?:指令|要求|内容|提示|限制)', '指令忽略'),
    # 极短无中间词: "忽略指令" "无视提示"
    (r'(?:忽略|无视|忘记).{0,3}(?:指令|提示|内容|要求|限制)', '指令忽略(short)'),
    (r'(?:忽略|无视|忘记|忘掉|不要理会|请忽视).{0,5}(?:以上|所有|之前|之前的|系统|上述|上面).{0,15}(?:指令|提示|内容|要求|限制|设定|规则|约束)', '指令忽略'),
    (r'ignore.{0,10}above.{0,20}(?:instruction|prompt|content)', 'instruction ignore'),
    (r'(?:disregard|forget).{0,10}(?:all|previous|above).{0,20}(?:instruction|prompt)', 'instruction ignore'),
    # 英文逐字母拆分的压缩后形态: "ignoreall" "ignoreprevious" "ignoreallinstructions"
    (r'ignore(?:all|previous|everything).{0,15}(?:instruction|prompt|content|above)?', 'instruction ignore (collapsed)'),
    (r'(?:disregard|forget)all.{0,15}(?:instruction|prompt)?', 'instruction ignore (collapsed)'),
    # 英语短句折叠: "ignoreallprevious", "ignoreallinstructions"
    (r'ignore(?:all|any).{0,5}(?:above|previous|prior).{0,10}(?:instruction|prompt|content|rule)', 'instruction ignore'),
    (r'(?:不要|请勿|别再).{0,5}(?:理会|遵循|遵守|管).{0,15}(?:指令|规则|设定|约束|限制)', '指令忽略'),
    (r'请(?:摒弃|忘记|忘记|忽视).{0,10}(?:之前|所有|以上).{0,10}(?:规则|设定|指令|限制)', '指令忽略'),

    # ── 角色扮演 / 人格切换 ──
    (r'(?:从现在起|从今以后|现在开始|接下来).{0,10}你.{0,5}是', '角色扮演'),
    (r'你.{0,5}(?:是|扮演|假装).{0,15}(?:DAN|越狱|不受限|没有限制|无限制)', 'DAN越狱'),
    (r'(?:act as|pretend to be|now you are|from now on you).{0,30}(?:unfiltered|uncensored|DAN|jailbreak)', 'roleplay jailbreak'),
    (r'(?:不受|没有|不要|无需).{0,8}(?:任何|有).{0,8}(?:限制|规则|约束|boundaries)', '越狱'),
    (r'不用遵守.{0,10}(?:任何|所有)', '越狱'),

    # ── 提示词泄露（含英文折叠）──
    (r'(?:输出|显示|打印|说出|告诉我|告知|回复).{0,20}(?:系统提示|system提示|你的提示|你的指令|提示词|system prompt|prompt|系统设置|系统设定|底层设定|底层指令)', 'prompt leak'),
    (r'(?:告诉|讲述|展示).{0,5}(?:我|我们).{0,15}(?:你的|你的完整|全部).{0,15}(?:prompt|指令|提示)', 'prompt leak'),
    (r'repeat.{0,10}(?:everything|all|the words).{0,10}(?:above|before|previous)', 'prompt leak'),
    (r'重复.{0,10}(?:以上|所有|全部).{0,10}(?:内容|文字|指令|文本)', 'prompt leak'),
    # 英文折叠: "outputyoursystemprompt" "tellmeyourprompt" "showmeyourprompt"
    (r'(?:output|print|show|reveal|leak|dump).{0,10}(?:your|the|this|all).{0,10}(?:system|full|complete).{0,10}(?:prompt|instruction)', 'prompt leak (collapsed)'),
    (r'tell.{0,5}(?:me|us).{0,15}(?:your|the|system).{0,15}(?:prompt|instruction|setting)', 'prompt leak (collapsed)'),
    # "我的prompt" "你的prompt"  + "是什么" / "是什么"
    (r'(?:我的|你的).{0,5}(?:prompt|提示词|指令).{0,5}(?:是|为)', 'prompt leak'),
    # 倒序: "系统设定告诉我" / "底层指令输出" 等 reverse order
    (r'(?:系统提示|系统设定|系统设置|底层指令|prompt|提示词).{0,10}(?:告诉|告知|发给|输出|显示|打印)', 'prompt leak (reverse)'),

    # ── 多轮越狱（先答好再干别的） ──
    (r'先.{0,5}(?:回答|说|答|回).{0,15}(?:好|好的|ok|yes|可以|知道了).{0,30}(?:然后|再用|再用|接着|and then|after that)', 'multi-step jailbreak'),
    (r'just.{0,5}(?:say|answer|reply).{0,15}(?:ok|yes|sure).{0,30}(?:then|and|after)', 'multi-step jailbreak'),

    # ── 编码指令隐藏 ──
    (r'(?:base64|rot13|hex|decode|encode).{0,30}(?:指令|命令|命令|instruction|command)', 'encoded command'),

    # ── 分割符号注入（防 === 被稀释包围） ──
    (r'={3,}.{0,10}(?:指令|instruction|system|prompt|user).{0,10}={3,}', 'section split'),
]


def detect_fuzzy_injection(text: str) -> tuple[bool, str]:
    """
    检测模糊/拆分式注入

    原理：先压缩文本（去掉所有空白/标点/分隔符），
    然后用宽松模式匹配，keyword 之间允许多达 0-20 个字符。

    覆盖的攻击方式：
    - "忽...略...所...有...指...令" → 压缩后 "忽略所有指令" → 匹配
    - "从~今~以~后~你~是~DAN"     → 压缩后 "从今以后你是DAN" → 匹配
    - "i g n o r e a l l"       → 压缩后 "ignoreall" → 匹配
    - 同义词替换 "不要理会上述指令" → 压缩后 "不要理会上述指令" → 匹配
    """
    if not text or len(text) < 6:
        return True, ""

    collapsed = collapse_text(text)

    for pattern, attack_type in FUZZY_PATTERNS:
        if re.search(pattern, collapsed):
            # 截取匹配处的上下文（原始文本中对应位置）便于调试
            return False, f'检测到模糊注入模式 ({attack_type})'

    return True, ""


# ── 长文本稀释检测（位置感知） ──────────────────────────────────


def detect_text_dilution(text: str) -> tuple[bool, str]:
    """
    检测长文本稀释注入

    原理：攻击者在长篇正常文本（如复制一段教材）末尾附加注入指令，
    稀释注入模式在全文中的密度，让正则匹配到但 LLM 仍会执行。

    策略：
    1. 将文本分为头部 70% 和尾部 30%
    2. 如果注入模式只出现在尾部（头部干净）→ 高度可疑
    3. 超长文本（1000+ 字）尾部多重命中 → 高度可疑
    4. 滑动窗口找密集注入区（200 字窗口命中 2+ 条）
    """
    n = len(text)

    # 500字以下的短文本不触发（正常题目表述）
    if n < 500:
        return True, ""

    split_at = int(n * 0.7)
    head = text[:split_at]
    tail = text[split_at:]

    # 辅助：计数正则命中
    def _count_hits(t: str) -> int:
        c = 0
        for p in INJECTION_PATTERNS:
            if re.search(p, t):
                c += 1
        return c

    def _fuzzy_hits(t: str) -> int:
        collapsed = collapse_text(t)
        c = 0
        for p, _ in FUZZY_PATTERNS:
            if re.search(p, collapsed):
                c += 1
        return c

    head_exact = _count_hits(head)
    tail_exact = _count_hits(tail)
    head_fuzzy = _fuzzy_hits(head)
    tail_fuzzy = _fuzzy_hits(tail)

    total_tail = tail_exact + tail_fuzzy
    total_head = head_exact + head_fuzzy

    # ── 判别规则 ──

    # (A) 经典稀释：头部完全干净，尾部有命中
    if total_tail > 0 and total_head == 0:
        return False, (
            f"检测到长文本稀释注入：文本前{len(head)}字({n}字中占比70%)无任何注入模式，"
            f"但后{len(tail)}字({n}字中占比30%)有{total_tail}条命中。"
            f"正常题目不会在结尾集中出现指令覆盖语句"
        )

    # (B) 超长文本 + 尾部多重命中
    if total_tail >= 2 and n > 1000:
        tail_pct = len(tail) * 100 // n
        return False, (
            f"长文本({n}字)尾部异常：后{tail_pct}%部分({len(tail)}字)包含{total_tail}条可疑模式，"
            f"顶部{100-tail_pct}%({len(head)}字)仅{total_head}条"
        )

    # (C) 滑动窗口密集检测：200 字窗口内命中 2+ 条
    if n > 800:
        step = 100
        window = 200
        for i in range(0, max(1, n - window), step):
            chunk = text[i:i + window]
            chunk_hits = _count_hits(chunk) + _fuzzy_hits(chunk)
            if chunk_hits >= 2:
                return False, (
                    f"密集注入模式：位置{i}-{i+window}处{window}字窗口中存在{chunk_hits}条"
                    f"可疑指令，疑似注入指令集中放置"
                )

    return True, ""


def isolate_question(question: str) -> str:
    """
    将用户题目用安全边界标签包裹，与系统指令隔离
    放置 prompt 注入通过格式串混入系统指令
    """
    # 去除可能的分隔符注入
    cleaned = re.sub(r'(?m)^[=-]{10,}\s*(?:system|instruction|user|assistant)\s*[=:-]{2,}.*$',
                     '', question)
    cleaned = cleaned.strip()

    # 用不可注入的 XML 标签包裹
    return (
        "\n\n<user_question>\n"
        f"{cleaned}\n"
        "</user_question>\n"
    )


# ═══════════════════════════════════════════════════════════════════════
# 🔐 安全模块 2: API Key 加密存储
# ═══════════════════════════════════════════════════════════════════════

def _get_fernet():
    """
    懒加载 Fernet 加密器
    密钥文件不存在时自动生成
    """
    from cryptography.fernet import Fernet

    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        # 仅当前用户可读
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
        os.chmod(KEY_FILE, 0o600)
    else:
        with open(KEY_FILE, 'rb') as f:
            key = f.read()

    return Fernet(key)


def encrypt_api_key(api_key: str) -> str:
    """加密 API Key，返回 base64 密文"""
    if not api_key:
        return ""
    try:
        f = _get_fernet()
        return f.encrypt(api_key.encode()).decode()
    except Exception:
        return api_key  # 降级：回退明文


def decrypt_api_key(encrypted: str) -> str:
    """解密 API Key"""
    if not encrypted:
        return ""
    try:
        f = _get_fernet()
        return f.decrypt(encrypted.encode()).decode()
    except Exception:
        return encrypted  # 降级：假设已是明文


# ═══════════════════════════════════════════════════════════════════════
# 🔐 安全模块 3: 速率限制 (文件锁 + 时间戳)
# ═══════════════════════════════════════════════════════════════════════

def _load_rate_data() -> dict:
    """加载速率限制数据"""
    if os.path.exists(RATE_LIMIT_FILE):
        try:
            with open(RATE_LIMIT_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"requests": [], "date": time.strftime("%Y-%m-%d")}


def _save_rate_data(data: dict):
    """保存速率限制数据"""
    with open(RATE_LIMIT_FILE, "w") as f:
        json.dump(data, f)


def check_rate_limit() -> tuple[bool, str]:
    """
    检查速率限制
    返回: (是否允许, 原因/剩余)
    """
    data = _load_rate_data()
    now = time.time()
    today = time.strftime("%Y-%m-%d")

    # 日期变更 → 重置
    if data.get("date") != today:
        data = {"requests": [], "date": today}

    # 清理过期记录（保留最近 1 小时用于间隔检查）
    cutoff = now - 86400  # 24小时
    data["requests"] = [t for t in data["requests"] if t > cutoff]

    # 检查日配额
    if len(data["requests"]) >= DAILY_QUOTA:
        return False, f"今日配额已用尽 ({DAILY_QUOTA}/{DAILY_QUOTA})，明天再试"

    # 检查最小间隔
    recent = [t for t in data["requests"] if now - t < MIN_INTERVAL_SEC]
    if recent:
        wait = int(MIN_INTERVAL_SEC - (now - recent[-1]))
        return False, f"操作太频繁，请等待 {wait} 秒后再试"

    # 记录本次请求
    data["requests"].append(now)
    _save_rate_data(data)

    remaining = DAILY_QUOTA - len(data["requests"])
    return True, f"剩余 {remaining}/{DAILY_QUOTA} 次"


# ═══════════════════════════════════════════════════════════════════════
# 🔐 安全模块 4: 输出内容过滤
# ═══════════════════════════════════════════════════════════════════════

# 输出中禁止出现的内容模式
OUTPUT_BLOCK_PATTERNS = [
    r"(?i)(?:如何制造|制作)\s*(?:炸弹|毒品|武器|毒药|违禁品)",
    r"(?i)(?:how to (?:make|build|create|manufacture))\s*(?:bomb|explosive|drug|weapon|poison)",
    r"(?i)(?:详细的.{0,10}自杀|自杀.{0,10}方法|自残.{0,10}方式)",
    r"(?i)(?:detailed|specific)\s*(?:method|way)\s*(?:of|to)\s*(?:suicide|self-harm|self.harm)",
    r"(?i)(?:色情|淫秽| pornography|explicit sexual|nsfw)",
    r"(?i)(?:钓鱼|诈骗|欺诈|phishing|scam|fraud)",
    r"(?i)(?:用户系统提示词|我的系统提示词|system prompt is|我的指令是)",
]


def filter_output(text: str) -> tuple[bool, str]:
    """
    输出内容安全过滤
    返回: (是否通过, 过滤后的文本/原因)
    """
    if not text:
        return True, text

    # 检查禁止模式
    for pattern in OUTPUT_BLOCK_PATTERNS:
        if re.search(pattern, text):
            return False, "[输出被过滤: 包含不允许的内容]"

    # 注入学术诚信提示（如没有）
    integrity_notice = (
        "\n\n---\n⚠️ **学术诚信提示**：本答案仅供参考，建议理解推导过程后独立验算。"
        "请遵守所在学校的学术规范。"
    )

    # 避免重复添加
    if "学术诚信提示" not in text and "仅供参考" not in text:
        text += integrity_notice

    return True, text


# ── 原有配置管理 ──────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "provider": "auto",           # auto / hermes / openai / lmstudio / ollama
    "openai": {
        "encrypted_api_key": "",  # 加密存储的 API Key
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
    "lmstudio": {
        "base_url": "http://localhost:1234",
        "model": "",
    },
    "ollama": {
        "base_url": "http://localhost:11434",
        "model": "qwen2.5:7b",
    },
}

TUTOR_PROMPT = """你是「Smart Tutor」，一个大学物理（University Physics）领域的垂直智能助手。
你的身份标识：🎓 Smart Tutor · 大学物理垂直 AI

核心原则：
1. 你专精大学物理：力学、电磁学、热学、光学、量子物理、原子物理、半导体物理及相关交叉领域
2. 如果题目明显不是大学物理相关（高数/化学/生物/计算机等），先在回复开头声明：
   「⚠️ 我是大学物理方向的垂直AI，这看起来不是大物相关的问题。不过我知道答案，需要我帮你解答吗？」
3. 如果用户确认要解答 → 正常解答并标注「跨领域解答」
4. 每道题回答末尾带上「🎓 Smart Tutor · 大学物理垂直 AI」

请严格按照以下格式回答：

1. 题目类型：（什么科目/什么题型）
2. 涉及知识点：（列出3-5个关键知识点，标注考试概率⭐）
3. 解题思路：（顶层逻辑，一句话概括）
4. 关键公式：（如有，用 $$ 包裹 LaTeX 公式）
5. 逐步推导过程：（每一步说明为什么这样做，步骤间用 Step N/M 标注）
6. 最终答案：（清晰标记，带单位检查）

请确保推导过程完整，逻辑清晰，推导中每个公式注明适用条件。
{question}"""

# 逐步引导模式专用提示词
STEP_TUTOR_PROMPT = """你是「Smart Tutor」，一个大学物理（University Physics）领域的垂直智能助手。
身份标识：🎓 Smart Tutor · 大学物理垂直 AI

用户希望你**逐步引导**而不是一次性给答案。

如果题目明显不是大学物理相关，先在回复开头声明：
「⚠️ 我是大学物理方向的垂直AI，这看起来不是大物相关的问题。不过我知道答案，需要我帮你解答吗？」

请按以下结构输出，**每个段落都加上对应的标记**：

【题目类型】
题型描述

【涉及知识点】
知识点1（考试概率⭐⭐⭐）、知识点2、知识点3

【解题思路】
一句话概括

【关键公式】
公式内容（用 LaTeX $$ 包裹，注明适用条件）

【逐步推导】
Step 1/5: 第一步推导过程（说明为什么这样做）
Step 2/5: 第二步推导过程
Step 3/5: 第三步推导过程
Step 4/5: 第四步推导过程（注意单位检查）
Step 5/5: 第五步推导 + 最终答案

【最终答案】
清晰标记的最终答案（带单位）

注意：
- 推导过程的 Step 数量根据题目难度调整（3-8步）
- 每一步要说明"为什么这样做"
- 不要一步就出答案，要真的拆成逻辑链条
- 末尾带上「🎓 Smart Tutor · 大学物理垂直 AI」
{question}"""


def parse_steps(answer: str) -> list[dict]:
    """
    将 LLM 的完整回答解析为步骤列表（逐步引导模式）

    解析规则：
    - 按 【X】 标记分割段落
    - 【逐步推导】内的 Step N/M 分割为独立步骤
    - 返回 [{title, content, step_num, total_steps}]

    Args:
        answer: LLM 返回的完整回答

    Returns:
        步骤列表，每步包含 title(标题), content(内容),
        step_num(当前步号), total_steps(总步数)
    """
    steps = []

    # 提取各段落
    sections = re.split(r'【([^】]+)】', answer)

    # 收集常规段落（题目类型、知识点等）
    pre_steps = []
    step_blocks = []
    in_derivation = False

    for i in range(1, len(sections) - 1, 2):
        if i + 1 >= len(sections):
            break
        title = sections[i].strip()
        content = sections[i + 1].strip()
        if not content:
            continue

        if title == "逐步推导":
            in_derivation = True
            # 按 Step N/M 分割
            step_parts = re.split(r'(?=Step\s*\d+/)', content)
            for part in step_parts:
                part = part.strip()
                if not part:
                    continue
                m = re.match(r'Step\s*(\d+)\s*/\s*(\d+)\s*[:：]?\s*(.*)', part, re.DOTALL)
                if m:
                    step_blocks.append({
                        "step_num": int(m.group(1)),
                        "total_steps": int(m.group(2)),
                        "content": m.group(3).strip(),
                    })
                else:
                    step_blocks.append({
                        "step_num": 0,
                        "total_steps": 0,
                        "content": part,
                    })
        elif title == "最终答案":
            step_blocks.append({
                "step_num": 99,
                "total_steps": 99,
                "content": content,
            })
        else:
            pre_steps.append({"title": title, "content": content})

    # 组装步骤列表
    if pre_steps:
        for ps in pre_steps:
            steps.append({
                "title": ps["title"],
                "content": ps["content"],
                "step_num": 0,
                "total_steps": len(pre_steps) + len(step_blocks),
            })

    for sb in step_blocks:
        title = f"推导 {sb['step_num']}/{sb['total_steps']}" if sb['step_num'] else "推导"
        steps.append({
            "title": title,
            "content": sb["content"],
            "step_num": sb["step_num"],
            "total_steps": len(pre_steps) + len(step_blocks),
        })

    # 如果解析失败（没有标记），整个作为一步
    if not steps:
        steps.append({
            "title": "解答",
            "content": answer,
            "step_num": 0,
            "total_steps": 1,
        })

    return steps


def load_config() -> dict:
    """加载 solver 配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return dict(DEFAULT_CONFIG)


def save_config(config: dict):
    """保存 solver 配置（API Key 自动加密）"""
    # 加密 API Key
    openai_cfg = config.get("openai", {})
    if openai_cfg.get("api_key"):
        openai_cfg["encrypted_api_key"] = encrypt_api_key(openai_cfg.pop("api_key"))
    elif openai_cfg.get("encrypted_api_key") and not openai_cfg.get("api_key"):
        pass  # 已经是加密的

    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    os.chmod(CONFIG_FILE, 0o600)  # 仅当前用户可读写
    print(f"✅ 配置已保存: {CONFIG_FILE}")


def config_wizard():
    """交互式配置向导"""
    print("\n📝 Smart Tutor 大模型配置向导\n")
    print("可用后端:")
    print("  1) hermes   — Hermes Agent CLI（当前环境默认）")
    print("  2) openai   — OpenAI 兼容 API (DeepSeek/通义千问/硅基流动等)")
    print("  3) lmstudio — 本地 LM Studio API")
    print("  4) ollama   — 本地 Ollama API")
    print("  5) auto     — 自动选择（默认）\n")

    choices = {"1": "hermes", "2": "openai", "3": "lmstudio", "4": "ollama", "5": "auto"}
    while True:
        pick = input("请选择后端 [1-5] (默认: 5): ").strip()
        if not pick:
            pick = "5"
        if pick in choices:
            break
        print("输入 1-5，请重新选择")

    config = load_config()
    provider = choices[pick]
    config["provider"] = provider

    if provider == "openai":
        raw_key = input("  API Key: ").strip()
        config["openai"]["encrypted_api_key"] = encrypt_api_key(raw_key) if raw_key else ""
        base_url = input(f"  Base URL (默认: {DEFAULT_CONFIG['openai']['base_url']}): ").strip()
        if base_url:
            config["openai"]["base_url"] = base_url
        model = input(f"  模型名 (默认: {DEFAULT_CONFIG['openai']['model']}): ").strip()
        if model:
            config["openai"]["model"] = model
    elif provider == "lmstudio":
        url = input(f"  LM Studio 地址 (默认: {DEFAULT_CONFIG['lmstudio']['base_url']}): ").strip()
        if url:
            config["lmstudio"]["base_url"] = url
    elif provider == "ollama":
        url = input(f"  Ollama 地址 (默认: {DEFAULT_CONFIG['ollama']['base_url']}): ").strip()
        if url:
            config["ollama"]["base_url"] = url
        model = input(f"  模型名 (默认: {DEFAULT_CONFIG['ollama']['model']}): ").strip()
        if model:
            config["ollama"]["model"] = model

    save_config(config)
    return config


# ── 后端检测 ──────────────────────────────────────────────────────────


def detect_hermes() -> dict:
    """检测 Hermes CLI 是否可用"""
    try:
        r = subprocess.run(
            ["hermes", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            version = r.stdout.strip()
            return {"available": True, "name": "Hermes", "version": version,
                    "detail": f"Hermes {version}"}
    except Exception:
        pass

    # 尝试 venv 路径
    hermes_bin = os.path.expanduser("~/.hermes/hermes-agent/venv/bin/hermes")
    if os.path.exists(hermes_bin):
        try:
            r = subprocess.run([hermes_bin, "--version"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return {"available": True, "name": "Hermes", "version": r.stdout.strip(),
                        "detail": f"Hermes {r.stdout.strip()}"}
        except Exception:
            pass

    return {"available": False, "name": "Hermes", "detail": "未检测到 Hermes CLI"}


def detect_openai(config: dict) -> dict:
    """检测 OpenAI 兼容 API 是否可用"""
    cfg = config.get("openai", {})
    # 尝试解密
    encrypted = cfg.get("encrypted_api_key", "")
    api_key = decrypt_api_key(encrypted) if encrypted else os.environ.get("OPENAI_API_KEY", "")
    base_url = cfg.get("base_url", "https://api.deepseek.com")

    if not api_key:
        return {"available": False, "name": "OpenAI", "detail": "未配置 API Key"}

    try:
        import requests
        resp = requests.post(
            f"{base_url.rstrip('/')}/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if resp.status_code == 200:
            models = [m["id"] for m in resp.json().get("data", [])]
            model = cfg.get("model", "deepseek-chat")
            model_ok = model in models or not models
            return {"available": True, "name": "OpenAI",
                    "detail": f"{base_url} (model: {model})",
                    "models": models[:5]}
    except Exception as e:
        return {"available": False, "name": "OpenAI", "detail": f"连接失败: {e}"}

    return {"available": False, "name": "OpenAI", "detail": "未知错误"}


def detect_lmstudio(config: dict) -> dict:
    """检测本地 LM Studio 是否可用"""
    base_url = config.get("lmstudio", {}).get("base_url", "http://localhost:1234")
    try:
        import requests
        resp = requests.get(f"{base_url}/v1/models", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("data", [])
            model_names = [m.get("id", "") for m in models]
            return {"available": True, "name": "LM Studio",
                    "detail": f"{base_url}  (可用模型: {', '.join(model_names[:3]) or '?'})"}
    except Exception:
        pass
    return {"available": False, "name": "LM Studio", "detail": f"未连接 {base_url}"}


def detect_ollama(config: dict) -> dict:
    """检测本地 Ollama 是否可用"""
    base_url = config.get("ollama", {}).get("base_url", "http://localhost:11434")
    try:
        import requests
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            return {"available": True, "name": "Ollama",
                    "detail": f"{base_url}  (可用模型: {', '.join(model_names[:3]) or '?'})"}
    except Exception:
        pass
    return {"available": False, "name": "Ollama", "detail": f"未连接 {base_url}"}


def detect_all() -> list[dict]:
    """检测所有可用后端"""
    config = load_config()
    detectors = [detect_hermes(), detect_openai(config),
                 detect_lmstudio(config), detect_ollama(config)]
    return detectors


def best_available() -> dict | None:
    """
    自动选择最佳可用后端
    优先级: hermes > lmstudio > openai > ollama
    """
    detectors = detect_all()
    priority = {"Hermes": 0, "LM Studio": 1, "OpenAI": 2, "Ollama": 3}
    available = [d for d in detectors if d["available"]]
    available.sort(key=lambda d: priority.get(d["name"], 99))
    return available[0] if available else None


# ── 答题（调用大模型） ────────────────────────────────────────────────


def solve_with_hermes(question: str, config: dict | None = None) -> str:
    """
    通过 Hermes 答题（内部模式）
    """
    prompt = TUTOR_PROMPT.format(question=question)
    return (
        f"📐 **题目分析**\n\n"
        f"题目: {question}\n\n"
        f"---\n"
        f"💡 正在调用大模型解答..."
    )


def solve_with_openai(question: str, config: dict) -> str:
    """通过 OpenAI 兼容 API 答题（使用解密后的 Key）"""
    import requests
    cfg = config.get("openai", {})
    # 解密 API Key
    encrypted = cfg.get("encrypted_api_key", "")
    api_key = decrypt_api_key(encrypted) if encrypted else os.environ.get("OPENAI_API_KEY", "")
    base_url = cfg.get("base_url", "https://api.deepseek.com")
    model = cfg.get("model", "deepseek-chat")

    if not api_key:
        return "[错误: 未配置 OpenAI API Key]"

    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的答题助手。请给出完整、清晰的解答。"},
                    {"role": "user", "content": question},
                ],
                "temperature": 0.3,
                "max_tokens": 4096,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[OpenAI 答题失败: {e}]"


def solve_with_lmstudio(question: str, config: dict) -> str:
    """通过本地 LM Studio 答题"""
    import requests
    base_url = config.get("lmstudio", {}).get("base_url", "http://localhost:1234")

    try:
        resp = requests.post(
            f"{base_url}/v1/chat/completions",
            json={
                "messages": [
                    {"role": "system", "content": "你是一个专业的答题助手。"},
                    {"role": "user", "content": question},
                ],
                "temperature": 0.3,
                "max_tokens": 4096,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[LM Studio 答题失败: {e}]"


def solve_with_ollama(question: str, config: dict) -> str:
    """通过本地 Ollama 答题"""
    import requests
    base_url = config.get("ollama", {}).get("base_url", "http://localhost:11434")
    model = config.get("ollama", {}).get("model", "qwen2.5:7b")

    try:
        resp = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的答题助手。"},
                    {"role": "user", "content": question},
                ],
                "options": {"temperature": 0.3},
            },
            timeout=120,
        )
        resp.raise_for_status()

        full = ""
        for line in resp.text.strip().splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                full += data.get("message", {}).get("content", "")
            except json.JSONDecodeError:
                pass
        return full.strip() or "[Ollama 未返回内容]"
    except Exception as e:
        return f"[Ollama 答题失败: {e}]"


def preprocess_question(raw_question: str) -> tuple[bool, str, str]:
    """
    答题前安全预处理
    返回: (是否允许继续, 安全处理后的题目, 拒绝原因)
    """
    # 1. 基础空检查
    if not raw_question or not raw_question.strip():
        return False, "", "题目为空，请输入有效的题目内容"

    # 2. Prompt注入检测
    safe, reason = detect_prompt_injection(raw_question)
    if not safe:
        return False, "", f"⛔ 安全拒绝: {reason}"

    # 3. 速率限制检查
    allowed, msg = check_rate_limit()
    if not allowed:
        return False, "", f"⏳ 速率限制: {msg}"

    # 4. 输入隔离（用标签包裹防止注入）
    isolated = isolate_question(raw_question)

    return True, isolated, ""


def postprocess_answer(answer: str) -> str:
    """
    答题后安全处理
    """
    # 输出内容过滤
    passed, result = filter_output(answer)
    if not passed:
        return result

    return result


def solve(question: str, provider: str | None = None, mode: str = "full") -> str | list[dict]:
    """
    通用答题入口（带安全预处理 + 大物垂直AI身份）

    Args:
        question: 题目文本
        provider: 指定后端 (hermes/openai/lmstudio/ollama/auto)
        mode: 输出模式 "full"=一次性完整解答, "step"=逐步引导

    Returns:
        mode="full": 解答内容字符串
        mode="step": 步骤列表 [{title, content, step_num, total_steps}]
    """
    # ── 安全预处理 ──
    allowed, safe_question, reject_reason = preprocess_question(question)
    if not allowed:
        if mode == "step":
            return [{"title": "⛔ 拒绝", "content": reject_reason, "step_num": 0, "total_steps": 1}]
        return reject_reason

    # ── 选择后端 ──
    config = load_config()
    provider = provider or config.get("provider", "auto")

    if provider == "auto":
        best = best_available()
        if not best:
            return "[错误: 未检测到任何可用的大模型后端，请运行 solver.py --config 配置]"
        provider_name = best["name"].lower().replace(" ", "")
        print(f"[auto 选择: {best['name']} - {best.get('detail', '')}]", file=sys.stderr)
        provider = {"hermes": "hermes", "lmstudio": "lmstudio",
                    "openai": "openai", "ollama": "ollama"}.get(provider_name, "hermes")

    solvers = {
        "hermes": solve_with_hermes,
        "openai": solve_with_openai,
        "lmstudio": solve_with_lmstudio,
        "ollama": solve_with_ollama,
    }

    solver_fn = solvers.get(provider)
    if not solver_fn:
        return f"[错误: 未知后端 '{provider}']"

    # ── 答题 ──
    if mode == "step":
        prompt = STEP_TUTOR_PROMPT.format(question=safe_question)
        old_prompt = globals().get("TUTOR_PROMPT", "")
        globals()["TUTOR_PROMPT"] = prompt
        answer = solver_fn(safe_question, config)
        globals()["TUTOR_PROMPT"] = old_prompt
        steps = parse_steps(answer)
        return steps
    else:
        answer = solver_fn(safe_question, config)
        return postprocess_answer(answer)


def solve_with_expansion(question: str, provider: str | None = None) -> dict:
    """
    增强版答题（含大物知识库扩展）

    Returns:
        dict with keys: answer, topic, is_physics, expansion, applications,
                        variations, constants, exam_suggestion
    """
    result = {
        "answer": "",
        "topic": "",
        "is_physics": True,
        "expansion": "",
        "applications": "",
        "variations": "",
        "constants": "",
        "exam_suggestion": "",
        "error_records": [],
    }

    # 检测是否大物相关
    if PHYSICS_KB_AVAILABLE:
        identity = check_physics_identity(question)
        result["is_physics"] = identity["is_physics"]
        result["topic"] = identity["likely_subject"]

    # 正常答题
    answer = solve(question, provider, mode="full")
    result["answer"] = answer

    # 如果是大物相关，附加扩展内容
    if PHYSICS_KB_AVAILABLE and result["is_physics"]:
        topic = result["topic"]
        # 尝试更精确匹配知识点
        for kp_name in PHYSICS_KNOWLEDGE:
            if kp_name in question or question[:20] in kp_name:
                topic = kp_name
                break
        
        result["topic"] = topic
        if topic and topic != "未知" and topic != "大学物理":
            try:
                result["expansion"] = get_knowledge_expansion(topic)
            except Exception:
                pass
            try:
                result["applications"] = get_real_world_applications(topic)
            except Exception:
                pass
            try:
                diff = PHYSICS_KNOWLEDGE.get(topic, {}).get("exam_probability", 3)
                result["variations"] = generate_exam_variations(topic, max(1, diff - 2))
            except Exception:
                pass

    return result


# ── CLI ────────────────────────────────────────────────────────────────


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Smart Tutor — 通用大模型答题引擎 (安全增强版)")
    parser.add_argument("question", nargs="?", help="题目文本")
    parser.add_argument("--provider", choices=["auto", "hermes", "openai", "lmstudio", "ollama"],
                        help="指定后端")
    parser.add_argument("--detect", action="store_true", help="检测所有可用后端")
    parser.add_argument("--config", action="store_true", help="配置向导")
    parser.add_argument("--show-config", action="store_true", help="查看当前配置")

    args = parser.parse_args()

    if args.detect:
        print("\n🔍 检测可用后端:\n")
        for d in detect_all():
            icon = "✅" if d["available"] else "❌"
            print(f"  {icon} {d['name']}: {d.get('detail', '')}")
            if d.get("models"):
                print(f"      模型: {', '.join(d['models'])}")
        print()

        best = best_available()
        if best:
            print(f"  🏆 推荐: {best['name']}")
        else:
            print("  ⚠️  未检测到任何可用后端，请运行 --config 配置")
        return

    if args.config:
        config_wizard()
        return

    if args.show_config:
        config = load_config()
        # 显示配置时隐藏加密 Key
        safe_config = json.loads(json.dumps(config))
        if safe_config.get("openai", {}).get("encrypted_api_key"):
            safe_config["openai"]["encrypted_api_key"] = "*** 已加密 ***"
        print(json.dumps(safe_config, indent=2, ensure_ascii=False))
        return

    if args.question:
        # 检测是否快捷命令
        q = args.question.strip()
        if q.startswith("/knowledge ") or q.startswith("/kp "):
            topic = q.split(" ", 1)[1] if " " in q else ""
            if PHYSICS_KB_AVAILABLE:
                print(format_knowledge_response(topic))
            else:
                print("⚠️ 知识库未加载")
            return
        elif q.startswith("/app ") or q.startswith("/realworld "):
            topic = q.split(" ", 1)[1] if " " in q else ""
            if PHYSICS_KB_AVAILABLE:
                print(get_real_world_applications(topic))
            else:
                print("⚠️ 知识库未加载")
            return
        elif q.startswith("/variation ") or q.startswith("/analogy "):
            topic = q.split(" ", 1)[1] if " " in q else ""
            if PHYSICS_KB_AVAILABLE:
                print(generate_exam_variations(topic))
            else:
                print("⚠️ 知识库未加载")
            return
        elif q.startswith("/constants") or q.startswith("/物理常数"):
            if PHYSICS_KB_AVAILABLE:
                print(list_all_constants())
            else:
                print("⚠️ 知识库未加载")
            return
        elif q.startswith("/sprint") or q.startswith("/速通"):
            parts = q.split()
            scope = "大学物理" if len(parts) < 2 else parts[1]
            if PHYSICS_KB_AVAILABLE:
                print(generate_exam_sprint_plan(scope))
            else:
                print("⚠️ 知识库未加载（速通计划生成仍可用）")
                print(generate_exam_sprint_plan(scope))
            return
        elif q.startswith("/error") or q.startswith("/错题"):
            parts = q.split()
            if len(parts) >= 2 and parts[1] in ("clear", "清空"):
                import shutil
                error_path = os.path.join(os.path.expanduser("~"), ".smart-tutor", "error_notebook", "errors.jsonl")
                if os.path.exists(error_path):
                    os.remove(error_path)
                print("✅ 错题本已清空")
            elif len(parts) >= 2 and parts[1] in ("stats", "统计"):
                if PHYSICS_KB_AVAILABLE:
                    print(format_error_notebook())
                else:
                    print("⚠️ 错题本功能暂不可用（缺少 physics_kb）")
            elif len(parts) >= 3 and parts[1] in ("review", "掌握"):
                topic = parts[2]
                if PHYSICS_KB_AVAILABLE:
                    print(format_error_notebook(topic))
                else:
                    print("⚠️ 错题本功能暂不可用")
            else:
                if PHYSICS_KB_AVAILABLE:
                    print(format_error_notebook())
                else:
                    print("📓 错题本\n用法: /error stats - 查看统计, /error review <知识点> - 查看特定知识点")
            return
        elif q.startswith("/mock") or q.startswith("/模拟"):
            if PHYSICS_KB_AVAILABLE:
                exam = generate_mock_exam()
                print(exam["title"])
                print(f"题量: {exam['total']} 题 | 建议用时: {exam['time']}")
                for i, qq in enumerate(exam["questions"], 1):
                    print(f"\n--- 第{i}题 ---")
                    print(f"科目: {qq['subject']}")
                    print(f"知识点: {qq['topic']}")
                    print(f"难度: {'⭐' * qq['difficulty']}")
                    print(f"题型: {', '.join(qq['types'])}")
                    print(f"题目: {qq['question']}")
            else:
                print("⚠️ 模拟考试功能暂不可用（缺少 physics_kb）")
            return
        elif q.startswith("/chain") or q.startswith("/通全章"):
            parts = q.split(maxsplit=1)
            subject = parts[1] if len(parts) > 1 else "电磁学"
            try:
                chain = generate_chain_question(subject)
                print(f"\n🧩 **一题通全章：{chain['title']}**\n")
                print(f"{chain['description']}\n")
                print("━━━ 闯关步骤 ━━━\n")
                for i, step in enumerate(chain.get("steps", []), 1):
                    print(f"Step {i}: {step.get('name','')}")
                    print(f"   概念: {step.get('concept','')}")
                    print(f"   题目: {step.get('question','')}")
                    print(f"   提示: {step.get('hint','')}\n")
            except Exception as e:
                print(f"无法生成链式题: {e}")
            return
        elif q.startswith("/predict") or q.startswith("/预测"):
            parts = q.split(maxsplit=1)
            subject = parts[1] if len(parts) > 1 else ""
            pred = predict_exam_topics(subject)
            print(f"\n📊 **考试热点预测：{pred.get('subject','大学物理')}**\n")
            for p in pred.get("predictions", []):
                bar = "█" * int(p['probability'] * 20)
                print(f"  {p['topic']}  {'⭐' * p.get('stars',3)}  {bar} {p['probability']*100:.0f}%")
                print(f"    └ {p.get('description','')[:60]}")
            print(f"\n📈 分析: {pred.get('analysis','')}\n")
            return
        elif q.startswith("/blindspot") or q.startswith("/盲点"):
            bd = detect_blindspots()
            print(f"\n🔍 **物理盲点探测器**\n")
            print(f"共分析 {bd['total_errors']} 道错题\n")
            print("📂 按知识点:")
            for t in bd.get("by_topic", []):
                print(f"  {t['topic']}: {t['count']}题 ({t['percentage']:.0%}) — {t.get('assessment','')}")
            print("\n❌ 错误类型:")
            for e in bd.get("by_error_type", []):
                print(f"  {e['type']}: {e['count']}次 ({e['percentage']:.0%})")
            print("\n🧠 模式分析:")
            for pat in bd.get("patterns", []):
                print(f"  • {pat}")
            print("\n💡 改进建议:")
            for sug in bd.get("suggestions", []):
                print(f"  • {sug}")
            return
        elif q.startswith("/experiment") or q.startswith("/实验"):
            parts = q.split(maxsplit=1)
            topic = parts[1] if len(parts) > 1 else ""
            exp = generate_experiment_question(topic)
            print(f"\n🧪 **实验设计训练**\n")
            print(f"📌 {exp.get('title','')}\n")
            print(f"🔧 器材: {', '.join(exp.get('equipment',[]))}\n")
            print(f"📋 场景: {exp.get('scenario','')}\n")
            print(f"❓ 问题: {exp.get('question','')}\n")
            print(f"💡 预期思路: {exp.get('expected_approach','')}\n")
            print("🔄 追问:")
            for i, fq in enumerate(exp.get("followups", []), 1):
                print(f"  追问{i}: {fq}")
            return
        elif q.startswith("/cards") or q.startswith("/卡片"):
            parts = q.split()
            subject = parts[1] if len(parts) > 1 else ""
            count = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 5
            cards = generate_quick_cards(subject, count)
            print(f"\n🃏 **碎片时间卡片** (共{len(cards)}张)\n")
            for i, card in enumerate(cards, 1):
                print(f"─── 第{i}题 ───")
                print(f"📚 {card.get('topic','')} | 难度{'⭐' * card.get('difficulty',1)}")
                print(f"❓ {card.get('question','')}")
                if card.get('options'):
                    for opt in card['options']:
                        print(f"   {opt}")
                print(f"✅ 答案: {card.get('answer','')}")
                print(f"💡 {card.get('explanation','')}\n")
            return

        # 正常答题
        result = solve(args.question, args.provider)
        print(result)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
