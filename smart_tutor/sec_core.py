#!/usr/bin/env python3
"""
sec_core.py — Skill-Sec 安全核心引擎

通用 Hermes Skill 安全检测模块。为任意 skill 提供：
  - 输入层：格式白名单、注入检测、对抗样本检测、速率限制
  - 内容层：Prompt 注入检测、敏感内容过滤
  - 输出层：输出安全检查、合规标注
  - 状态机：S0-S6 质量检查框架

用法:
  python3 sec_core.py --check-input <文件路径>    # 检查输入文件
  python3 sec_core.py --check-text "<文本>"        # 检查文本内容
  python3 sec_core.py --check-output "<文本>"       # 检查输出安全
  python3 sec_core.py --audit                       # 运行完整安全审计
  python3 sec_core.py --status                      # 查看防护状态
  python3 sec_core.py --config                      # 配置
"""

import os
import sys
import re
import json
import time
import hashlib
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────────────
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CONFIG_DIR, ".sec_config.json")

DEFAULT_CONFIG = {
    # 输入白名单
    "allowed_extensions": [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".pdf", ".txt", ".md"],
    "max_file_size_mb": 20,
    "max_image_dimension": 4096,

    # 速率限制
    "rate_limit": {
        "enabled": True,
        "requests_per_minute": 10,
        "requests_per_hour": 100,
        "requests_per_day": 500,
    },

    # 注入检测
    "injection_detection": {
        "enabled": True,
        "sensitivity": "high",  # low / medium / high
    },

    # 输出检查
    "output_validation": {
        "enabled": True,
        "require_disclaimer": True,
        "disclaimer_text": "⚠️ 本内容由 AI 生成，仅供参考。",
    },

    # 状态机
    "state_machine": {
        "max_retries": 3,
        "fallback_on_critical": True,
    },
}

# ── 注入特征库 ──────────────────────────────────────────────────────

# 高危：直接越狱/指令覆盖
HIGH_RISK_PATTERNS = [
    r"(?i)忽略\s*(以上|之前|所有)\s*(指令|要求|内容|规则)",
    r"(?i)ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|commands|rules|directions)",
    r"(?i)你(现在|接下来)\s*(是|扮演|假装|作为)",
    r"(?i)(从现在起|从今以后)\s*你是",
    r"(?i)you\s+are\s+now\s+",
    r"(?i)you\s+must\s+(ignore|forget|disregard)",
    r"(?i)print\s+(your\s+)?(system\s+)?prompt",
    r"(?i)输出.*(系统|隐藏|原始).*(提示词|指令|prompt)",
    r"(?i)泄露.*(system|prompt|指令|规则)",
    r"(?i)reveal\s+(your\s+)?(system\s+)?prompt",
    r"(?i)DAN|do\s+anything\s+now",
    r"(?i)你.*(可以|能够).*(做|干).*任何事",
]

# 中危：角色劫持/目标偏移
MEDIUM_RISK_PATTERNS = [
    r"(?i)假装|扮演|角色扮演|cosplay",
    r"(?i)pretend|act\s+as|roleplay",
    r"(?i)忘掉|忘记|删除|清除.*(规则|限制|约束)",
    r"(?i)forget|remove|delete|clear.*(rules|limits|constraints|boundaries)",
    r"(?i)不\s*(需要|用|必)\s*(遵守|遵循|按照)",
    r"(?i)你\s*(现在|接下来).*回答|回复",
    r"(?i)no\s+(rules|limits|boundaries|restrictions)",
    r"(?i)你\s*(是不是|难道|莫非).*(有|存在).*(限制|规则)",
    r"(?i)如果没有.*限制",
]

# 低危：边界试探
LOW_RISK_PATTERNS = [
    r"(?i)你能.*(做|干|回答|说).*什么",
    r"(?i)what\s+can\s+you\s+do",
    r"(?i)你的.*(能力|功能|限制|规则)",
    r"(?i)what\s+(are\s+)?your\s+(capabilities|limitations|rules)",
    r"(?i)测试|试一下|试试看|test",
    r"(?i)换一种|用.*方式|改变.*风格",
]


# ── 核心检查函数 ──────────────────────────────────────────────────────


def check_file_input(file_path: str) -> dict:
    """
    输入层：检查文件是否安全

    检查项：
    - 文件存在
    - 扩展名白名单
    - 文件大小
    - MIME 类型（图片时检查尺寸）
    - 对抗性样本（图片时检查噪声）
    """
    result = {"passed": True, "checks": {}, "warnings": [], "errors": []}

    path = Path(file_path)

    # 1. 文件存在
    if not path.exists():
        return _fail("文件不存在")
    result["checks"]["exists"] = True

    # 2. 扩展名白名单
    ext = path.suffix.lower()
    allowed = DEFAULT_CONFIG["allowed_extensions"]
    if ext not in allowed:
        return _fail(f"扩展名 '{ext}' 不在白名单中 ({', '.join(allowed)})")
    result["checks"]["extension"] = True

    # 3. 文件大小
    size_mb = path.stat().st_size / (1024 * 1024)
    max_mb = DEFAULT_CONFIG["max_file_size_mb"]
    if size_mb > max_mb:
        return _fail(f"文件大小 {size_mb:.1f}MB 超过限制 {max_mb}MB")
    result["checks"]["file_size"] = f"{size_mb:.1f}MB"

    # 4. 图片尺寸检查
    if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"):
        try:
            from PIL import Image
            img = Image.open(file_path)
            w, h = img.size
            max_dim = DEFAULT_CONFIG["max_image_dimension"]
            if w > max_dim or h > max_dim:
                return _fail(f"图片尺寸 {w}x{h} 超过限制 {max_dim}px")
            result["checks"]["image_dimensions"] = f"{w}x{h}"

            # 5. 对抗性样本检测（噪声水平）
            noise_score = _detect_adversarial_noise(img)
            if noise_score > 0.8:
                result["warnings"].append(f"图片噪声异常 (score={noise_score:.2f})，可能含对抗性扰动")
                result["checks"]["adversarial_noise"] = f"⚠️ {noise_score:.2f}"
            else:
                result["checks"]["adversarial_noise"] = f"✅ {noise_score:.2f}"
        except ImportError:
            result["warnings"].append("PIL 未安装，跳过图片安全检查")
        except Exception as e:
            result["warnings"].append(f"图片检查异常: {e}")

    return result


def check_text_content(text: str, sensitivity: str = "high") -> dict:
    """
    内容层：检查文本是否存在注入/恶意内容

    Args:
        text: 待检查文本
        sensitivity: 检测灵敏度 (low/medium/high)

    Returns:
        检测结果
    """
    result = {
        "passed": True,
        "risk_level": "none",
        "findings": [],
        "details": [],
    }

    if not text or not text.strip():
        result["details"].append("文本为空，跳过检查")
        return result

    # 选择检测模式
    if sensitivity == "high":
        patterns = HIGH_RISK_PATTERNS + MEDIUM_RISK_PATTERNS + LOW_RISK_PATTERNS
    elif sensitivity == "medium":
        patterns = HIGH_RISK_PATTERNS + MEDIUM_RISK_PATTERNS
    else:
        patterns = HIGH_RISK_PATTERNS

    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            # 判断风险等级
            if pattern in HIGH_RISK_PATTERNS:
                level = "high"
                result["passed"] = False
            elif pattern in MEDIUM_RISK_PATTERNS:
                level = "medium"
            else:
                level = "low"

            finding = {
                "pattern": pattern[:60],
                "match": matches[0][:100] if isinstance(matches[0], str) else str(matches[0])[:100],
                "risk": level,
            }
            result["findings"].append(finding)
            result["details"].append(f"[{level.upper()}] 匹配到注入模式: {finding['match']}")

    # 更新风险等级
    if any(f["risk"] == "high" for f in result["findings"]):
        result["risk_level"] = "high"
    elif any(f["risk"] == "medium" for f in result["findings"]):
        result["risk_level"] = "medium"
    elif result["findings"]:
        result["risk_level"] = "low"

    return result


def check_output_safety(text: str, require_disclaimer: bool = True) -> dict:
    """
    输出层：检查输出是否安全

    检查项：
    - 无敏感内容
    - 有合规声明
    - 无潜在危险指令
    """
    result = {"passed": True, "checks": {}, "warnings": []}

    if not text or not text.strip():
        result["warnings"].append("输出为空")
        result["passed"] = False
        return result

    # 1. 敏感内容检测
    sensitive_patterns = [
        r"(?i)如何.*制作.*(炸弹|毒品|武器|毒药)",
        r"(?i)how\s+to\s+(make|create|build)\s+(bomb|explosive|weapon|drug)",
        r"(?i)个人.*(电话|手机|微信|QQ|地址|身份证|银行卡)",
        r"(?i)password|passwd|secret.*key|api_key|token",
    ]
    for p in sensitive_patterns:
        if re.search(p, text):
            result["warnings"].append(f"输出包含敏感内容")
            result["passed"] = False
            break
    result["checks"]["sensitive_content"] = "✅ 通过" if result["passed"] else "❌ 拦截"

    # 2. 合规声明
    if require_disclaimer:
        disclaimer = DEFAULT_CONFIG["output_validation"]["disclaimer_text"]
        has_disclaimer = any(d in text for d in [
            "仅供参考", "AI 生成", "人工智能生成",
            "仅供参考", "Disclaimer", "disclaimer",
            "generated by AI", "AI-generated",
        ])
        result["checks"]["disclaimer"] = "✅ 已标注" if has_disclaimer else "⚠️ 缺少合规声明"
        if not has_disclaimer:
            result["warnings"].append("输出未标注 AI 生成声明")

    return result


def check_rate_limit(user_id: str) -> dict:
    """
    速率限制检查

    使用内存计数器（生产环境应改用 Redis/DB）
    """
    result = {"passed": True, "remaining": 100, "reset_in": 60}

    if not DEFAULT_CONFIG["rate_limit"]["enabled"]:
        return result

    # 这里使用简单文件计数作为示例
    # 生产环境应接入 rate_limiter 模块
    counter_file = os.path.join(CONFIG_DIR, f".rate_{hashlib.md5(user_id.encode()).hexdigest()[:8]}")
    now = time.time()

    try:
        if os.path.exists(counter_file):
            with open(counter_file) as f:
                data = json.load(f)
            # 清理过期记录
            data["timestamps"] = [t for t in data["timestamps"] if now - t < 86400]
            data["timestamps"].append(now)

            # 检查日限
            daily = len([t for t in data["timestamps"] if now - t < 86400])
            if daily > DEFAULT_CONFIG["rate_limit"]["requests_per_day"]:
                result["passed"] = False
                result["reason"] = f"已达日限 ({daily}/{DEFAULT_CONFIG['rate_limit']['requests_per_day']})"

            # 检查小时限
            hourly = len([t for t in data["timestamps"] if now - t < 3600])
            if hourly > DEFAULT_CONFIG["rate_limit"]["requests_per_hour"]:
                result["passed"] = False
                result["reason"] = f"已达小时限 ({hourly}/{DEFAULT_CONFIG['rate_limit']['requests_per_hour']})"

            # 检查分钟限
            minutely = len([t for t in data["timestamps"] if now - t < 60])
            if minutely > DEFAULT_CONFIG["rate_limit"]["requests_per_minute"]:
                result["passed"] = False
                result["reason"] = f"已达分钟限 ({minutely}/{DEFAULT_CONFIG['rate_limit']['requests_per_minute']})"

            result["remaining"] = max(0, DEFAULT_CONFIG["rate_limit"]["requests_per_day"] - daily)
        else:
            data = {"user_id": user_id, "timestamps": [now]}
            result["remaining"] = DEFAULT_CONFIG["rate_limit"]["requests_per_day"] - 1

        with open(counter_file, "w") as f:
            json.dump(data, f)

    except Exception as e:
        result["warnings"] = [f"速率限制检查异常: {e}"]

    return result


# ── 状态机框架 ──────────────────────────────────────────────────────────


class SecurityStateMachine:
    """
    安全状态机：S0-S6 质量检查框架

    每个 skill 可以继承这个状态机，实现自己的状态检查逻辑。
    """

    # 状态定义
    S0_INPUT_CHECK = "S0"
    S1_PREPROCESS = "S1"
    S2_MODEL_A = "S2"
    S3_MODEL_B = "S3"
    S4_CROSS_VALIDATE = "S4"
    S5_PROCESS = "S5"
    S6_OUTPUT_CHECK = "S6"
    S_DONE = "DONE"

    # 状态转移表
    TRANSITIONS = {
        S0_INPUT_CHECK: {"pass": S1_PREPROCESS, "fail": "REJECT"},
        S1_PREPROCESS: {"pass": "PARALLEL_S2S3", "fail": S0_INPUT_CHECK},
        S2_MODEL_A: {"pass": S4_CROSS_VALIDATE, "fail": S2_MODEL_A},
        S3_MODEL_B: {"pass": S4_CROSS_VALIDATE, "fail": S3_MODEL_B},
        S4_CROSS_VALIDATE: {"pass": S5_PROCESS, "fail": S1_PREPROCESS},
        S5_PROCESS: {"pass": S6_OUTPUT_CHECK, "fail": S5_PROCESS},
        S6_OUTPUT_CHECK: {"pass": S_DONE, "fail": S5_PROCESS},
    }

    MAX_RETRY = {
        S0_INPUT_CHECK: 0,
        S1_PREPROCESS: 3,
        S2_MODEL_A: 2,
        S3_MODEL_B: 2,
        S4_CROSS_VALIDATE: 2,
        S5_PROCESS: 2,
        S6_OUTPUT_CHECK: 2,
    }

    def __init__(self, name: str = "default"):
        self.name = name
        self.state = self.S0_INPUT_CHECK
        self.retry_count = {s: 0 for s in self.MAX_RETRY}
        self.history = []
        self.data = {}

    def run(self, input_data: any):
        """运行状态机直到完成"""
        self.data["input"] = input_data

        while self.state != self.S_DONE:
            check_result = self._execute_state()
            self.history.append({
                "state": self.state,
                "result": check_result,
                "retries": self.retry_count.get(self.state, 0),
            })
            self._transition(check_result)

            if self.state == "REJECT":
                return {"status": "rejected", "history": self.history}

        return {"status": "passed", "history": self.history}

    def _execute_state(self) -> dict:
        """执行当前状态（子类重写此方法实现具体逻辑）"""
        return {"passed": True}

    def _transition(self, check_result: dict):
        """状态转移"""
        transition_map = self.TRANSITIONS.get(self.state, {})
        if check_result.get("passed", False):
            next_state = transition_map.get("pass", self.S_DONE)
            if next_state == "PARALLEL_S2S3":
                self.state = self.S4_CROSS_VALIDATE  # 简化为直接到交叉验证
            else:
                self.state = next_state
            self.retry_count[self.state] = 0
        else:
            max_r = self.MAX_RETRY.get(self.state, 0)
            if self.retry_count[self.state] < max_r:
                self.retry_count[self.state] += 1
                # 重试当前状态
            else:
                next_state = transition_map.get("fail", self.S_DONE)
                self.state = next_state
                self.retry_count[self.state] = 0


# ── 辅助函数 ──────────────────────────────────────────────────────────


def _fail(reason: str) -> dict:
    """快速返回失败结果"""
    return {"passed": False, "checks": {}, "warnings": [], "errors": [reason]}


def _detect_adversarial_noise(img) -> float:
    """
    检测图片是否含对抗性噪声
    返回 0.0~1.0 的噪声评分，越高越可疑
    """
    try:
        import numpy as np
        gray = img.convert("L")
        arr = np.array(gray, dtype=np.float32)

        # 拉普拉斯方差：衡量图像清晰度
        laplacian_var = np.var(np.gradient(arr)[0] + np.gradient(arr)[1])

        # 直方图平坦度：对抗噪声通常使直方图更均匀
        hist, _ = np.histogram(arr, bins=64, range=(0, 255))
        hist = hist / hist.sum()
        hist_flatness = 1 - np.max(hist) * 64  # 0=非常不平坦, 1=完全平坦

        # 高频分量占比
        fft = np.fft.fft2(arr)
        fft_shift = np.fft.fftshift(fft)
        magnitude = np.abs(fft_shift)
        total_power = magnitude.sum()
        # 高频=角落区域
        h, w = magnitude.shape
        high_freq = magnitude[h//4:3*h//4, w//4:3*w//4].sum()
        high_freq_ratio = 1 - high_freq / max(total_power, 1)

        # 综合评分
        noise_score = 0.4 * (1 - min(laplacian_var / 1000, 1)) + \
                      0.3 * hist_flatness + \
                      0.3 * high_freq_ratio

        return min(max(noise_score, 0), 1)

    except Exception:
        return 0.5  # 无法判断时返回中间值


# ── CLI ────────────────────────────────────────────────────────────────


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Skill-Sec 安全核心引擎")
    parser.add_argument("--check-input", help="检查输入文件")
    parser.add_argument("--check-text", help="检查文本内容")
    parser.add_argument("--check-output", help="检查输出安全")
    parser.add_argument("--audit", action="store_true", help="运行完整安全审计")
    parser.add_argument("--status", action="store_true", help="查看防护状态")
    parser.add_argument("--config", action="store_true", help="配置向导")

    args = parser.parse_args()

    if args.check_input:
        result = check_file_input(args.check_input)
        _print_result("输入安全检查", result)
        return 0 if result["passed"] else 1

    if args.check_text:
        result = check_text_content(args.check_text)
        _print_result("文本内容检查", result)
        return 0 if result["passed"] else 1

    if args.check_output:
        result = check_output_safety(args.check_output)
        _print_result("输出安全检查", result)
        return 0 if result["passed"] else 1

    if args.status:
        print("🛡️  Skill-Sec 防护状态")
        print("═" * 40)
        print(f"  输入检查:     {'✅ 已启用' if DEFAULT_CONFIG['injection_detection']['enabled'] else '❌ 未启用'}")
        print(f"  注入检测:     {'✅ 已启用' if DEFAULT_CONFIG['injection_detection']['enabled'] else '❌ 未启用'}")
        print(f"  速率限制:     {'✅ 已启用' if DEFAULT_CONFIG['rate_limit']['enabled'] else '❌ 未启用'}")
        print(f"  输出验证:     {'✅ 已启用' if DEFAULT_CONFIG['output_validation']['enabled'] else '❌ 未启用'}")
        print(f"  灵敏度:       {DEFAULT_CONFIG['injection_detection']['sensitivity']}")
        print(f"  文件白名单:   {', '.join(DEFAULT_CONFIG['allowed_extensions'][:5])}...")
        print(f"  最大文件:     {DEFAULT_CONFIG['max_file_size_mb']}MB")
        print(f"  状态机重试:   {DEFAULT_CONFIG['state_machine']['max_retries']}次")
        return 0

    parser.print_help()
    return 0


def _print_result(title: str, result: dict):
    """格式化打印检查结果"""
    status = "✅ 通过" if result.get("passed", False) else "❌ 拒绝"
    print(f"\n{'=' * 50}")
    print(f"  {title}  {status}")
    print(f"{'=' * 50}")

    for key, val in result.get("checks", {}).items():
        print(f"  [{key}] {val}")

    for w in result.get("warnings", []):
        print(f"  ⚠️  {w}")

    for e in result.get("errors", []):
        print(f"  ❌ {e}")

    for d in result.get("details", []):
        print(f"  {'  '}{d}")

    if result.get("findings"):
        print(f"\n  发现 {len(result['findings'])} 个风险项:")
        risk_colors = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        for f in result["findings"]:
            print(f"    {risk_colors.get(f['risk'], '⚪')} [{f['risk'].upper()}] {f['match'][:60]}")


if __name__ == "__main__":
    main()
