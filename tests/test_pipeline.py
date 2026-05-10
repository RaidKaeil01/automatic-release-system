"""端到端 Pipeline 测试（不执行发布）"""
import json
import sys
sys.path.insert(0, ".")

from agents.planner_agent import PlannerAgent
from agents.writer_agent import WriterAgent


def test_planner():
    agent = PlannerAgent()
    outline = agent.plan("STM32 + YOLOv8 目标检测部署")
    assert "title" in outline
    assert "sections" in outline
    assert len(outline["sections"]) >= 3
    print(json.dumps(outline, ensure_ascii=False, indent=2))


def test_writer():
    outline = {
        "title": "STM32 + YOLOv8 目标检测部署教程",
        "description": "从零开始在 STM32 上部署 YOLOv8 目标检测模型",
        "tags": ["嵌入式", "AI", "YOLOv8"],
        "sections": [
            {
                "id": 1,
                "title": "环境搭建与工具链配置",
                "description": "搭建交叉编译环境，安装必要工具",
                "key_points": ["ARM GCC", "CMake", "OpenCV"],
                "code_language": "bash",
            }
        ],
    }
    agent = WriterAgent()
    md = agent.write(outline)
    assert len(md) > 100
    print(md[:500])


if __name__ == "__main__":
    test_planner()
