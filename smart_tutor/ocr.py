#!/usr/bin/env python3
"""
Smart Tutor OCR — 智能答题助手的本地OCR模块
替换原设计中的百度OCR（云端API），改用本地 Unlimited-OCR (3B MoE)。

配合 MiniCPM-V（LM Studio本地）做双模型交叉验证：
- MiniCPM: 整图语义理解、公式解析
- Unlimited-OCR: 印刷体文字精确提取（本地GPU，数据不出本机）

用法：
  python ocr.py <图片路径>                       # OCR识别题目文字
  python ocr.py <图片路径> --mode normal          # 通用模式
  python ocr.py <图片路径> --prompt "extract text" # 自定义prompt
"""
import sys
import os
import re
import json

# 复用 vision skill 的 Unlimited-OCR 封装
VISION_SKILL_DIR = os.path.expanduser("~/.hermes/skills/vision/scripts")


def is_available() -> bool:
    """检查 Unlimited-OCR 是否可用"""
    try:
        sys.path.insert(0, VISION_SKILL_DIR)
        from ocr_unlimited import is_available as _check
        return _check()
    except Exception:
        return False


def ocr_text(image_path: str, mode: str = "gundam",
             prompt: str = "document parsing.") -> str:
    """
    调用 Unlimited-OCR 提取题目文字
    
    Args:
        image_path: 图片路径
        mode: gundam(文档/公式) / normal(通用)
        prompt: OCR提示词
    
    Returns:
        提取到的文字内容
    """
    sys.path.insert(0, VISION_SKILL_DIR)
    from ocr_unlimited import ocr
    return ocr(image_path, mode=mode, prompt=prompt)


def mini_cpm_analyze(image_path: str, prompt: str = "请读出图片中的题目内容") -> str:
    """
    调用本地 LM Studio MiniCPM-V 做整图语义理解
    
    用于双模型交叉验证的第二路
    """
    import requests
    
    # LM Studio API 地址
    api_url = "http://localhost:1234/v1/chat/completions"
    
    import base64
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    
    # 判断图片格式
    ext = os.path.splitext(image_path)[1].lower()
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "png")
    
    payload = {
        "model": "minicpm-v-4.6",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{b64}"}},
                {"type": "text", "text": prompt}
            ]
        }],
        "max_tokens": 2048,
        "temperature": 0.1,
    }
    
    try:
        resp = requests.post(api_url, json=payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[MiniCPM 调用失败: {e}]"


def cross_validate(ocr_text: str, vision_text: str) -> tuple[str, float]:
    """
    双模型交叉验证：合并结果并评分
    
    Args:
        ocr_text: Unlimited-OCR 提取的文字
        vision_text: MiniCPM 理解的文字
    
    Returns:
        (合并后的题目文本, 置信度 0.0-1.0)
    """
    # 提取公共内容
    ocr_lines = set(ocr_text.strip().splitlines())
    vision_lines = set(vision_text.strip().splitlines())
    
    common = ocr_lines & vision_lines
    union = ocr_lines | vision_lines
    
    # 置信度: 公共部分占比
    if not union:
        merged = ocr_text or vision_text
        confidence = 0.3
    else:
        confidence = len(common) / max(len(union), 1)
        
        # OCR 对文字更准，用OCR为主
        if confidence < 0.3:
            # 差异大时，以OCR为准（文字精确性更高）
            merged = ocr_text
        else:
            merged = "\n".join(
                line for line in ocr_text.splitlines() if line.strip()
            ) if ocr_text.strip() else vision_text
    
    return merged.strip(), confidence


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Smart Tutor OCR — 本地双模型交叉验证")
    parser.add_argument("image_path", help="题目图片路径")
    parser.add_argument("--mode", choices=["gundam", "normal"], default="gundam",
                        help="OCR模式")
    parser.add_argument("--prompt", default="document parsing.",
                        help="OCR提示词")
    parser.add_argument("--no-cross", action="store_true",
                        help="跳过MiniCPM交叉验证（仅用Unlimited-OCR）")
    args = parser.parse_args()

    if not os.path.exists(args.image_path):
        print(f"❌ 文件不存在: {args.image_path}", file=sys.stderr)
        sys.exit(1)

    # 步骤1: Unlimited-OCR 提取文字
    if not is_available():
        print("❌ Unlimited-OCR 不可用（GPU/模型文件缺失）", file=sys.stderr)
        sys.exit(1)

    print("⏳ Unlimited-OCR 提取文字...", file=sys.stderr)
    ocr_result = ocr_text(args.image_path, args.mode, args.prompt)

    if args.no_cross:
        print(ocr_result)
        return

    # 步骤2: MiniCPM 整图理解
    print("⏳ MiniCPM 整图理解...", file=sys.stderr)
    vision_result = mini_cpm_analyze(args.image_path)

    # 步骤3: 交叉验证
    merged, confidence = cross_validate(ocr_result, vision_result)

    # 输出
    print(f"[交叉验证 置信度: {confidence:.1%}]")
    if merged:
        print(merged)
    else:
        print("(未识别到题目内容)", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
