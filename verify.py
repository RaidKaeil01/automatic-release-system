import re
import sys
sys.path.insert(0, '.')
from agents.publisher_agent import PublisherAgent
from pathlib import Path

md = Path('output/STM32_HAL_ADC高级用法：双ADC交替采样与DMA高效传输实战/tutorial_final.md').read_text(encoding='utf-8')
processed = PublisherAgent._preprocess_for_csdn(md)

# 1. Heading levels in original
headings = re.findall(r'^(#{1,6})\s+(.+)$', md, re.MULTILINE)
from collections import Counter
level_counts = Counter(len(h) for h, _ in headings)
print("=== 原始标题层级 ===")
for level in sorted(level_counts):
    examples = [t for h, t in headings if len(h) == level][:2]
    print(f"  {'#'*level}: {level_counts[level]} 个  例: {examples[0][:40]}")

# 2. Heading levels after preprocessing
headings_p = re.findall(r'^(#{1,6})\s+(.+)$', processed, re.MULTILINE)
level_counts_p = Counter(len(h) for h, _ in headings_p)
print("\n=== 预处理后标题层级 ===")
for level in sorted(level_counts_p):
    print(f"  {'#'*level}: {level_counts_p[level]} 个")

# 3. Code block check
code_blocks = re.findall(r'^```$', processed, re.MULTILINE)
print(f"\n=== 代码块 ===")
print(f"  代码块标记数: {len(code_blocks)} (应为偶数)")
print(f"  代码块数: {len(code_blocks)//2}")

# 4. Check code blocks have language tags stripped
openings = re.findall(r'^`{3}\w+$', processed, re.MULTILINE)
print(f"  带语言标记的代码块: {len(openings)} (应为0)")

# 5. Check code block spacing
lines = processed.split('\n')
spacing_issues = []
in_code = False
for i, line in enumerate(lines):
    if line.startswith('```'):
        if not in_code and i > 0 and lines[i-1].strip():
            spacing_issues.append(f"Line {i+1}: 开始标记前无空行")
        elif in_code and i < len(lines)-1 and lines[i+1].strip():
            spacing_issues.append(f"Line {i+1}: 结束标记后无空行")
        in_code = not in_code
print(f"  代码块间距问题: {len(spacing_issues)}")

# 6. Show first 30 lines
print("\n=== 文档前30行 ===")
for i, line in enumerate(processed.split('\n')[:30], 1):
    print(f"  {i:3d}: {line[:100]}")

# 7. Total size
print(f"\n=== 总计 ===")
print(f"  字符数: {len(processed)}")
print(f"  行数: {len(processed.split(chr(10)))}")
