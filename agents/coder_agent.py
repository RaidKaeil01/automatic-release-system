import re
from agents.base import BaseAgent

SYSTEM_PROMPT = """你是一个 Mermaid 图表代码专家。根据用户描述的内容，生成可直接渲染的 Mermaid 代码。

支持的图表类型：
- flowchart TD/LR — 流程图
- sequenceDiagram — 时序图
- classDiagram — 类图
- stateDiagram-v2 — 状态图
- erDiagram — ER 图
- graph TD/LR — 通用关系图

要求：
1. 严格只输出 Mermaid 代码块，不要输出任何解释、注释或 markdown 包裹
2. 代码必须语法正确，可直接被 mermaid-cli 渲染
3. 使用中文标签（节点文字用中文）
4. 节点 ID 使用英文（如 A、B、C 或 node1、node2）
5. 代码第一行必须是图表类型声明（如 flowchart TD）
6. 合理布局，避免节点过多导致图过大（控制在 15 个节点以内）"""


class CoderAgent(BaseAgent):
    def generate_mermaid(self, description: str, diagram_type: str = "flowchart") -> str:
        """根据描述生成 Mermaid 代码

        Args:
            description: 图表内容描述
            diagram_type: 图表类型（flowchart/sequence/class/state/er/graph）

        Returns:
            Mermaid 代码字符串
        """
        user_prompt = f"""请为以下内容生成 Mermaid {diagram_type} 代码：

{description}

要求：
- 图表类型：{diagram_type}
- 使用中文标签
- 节点 ID 用英文
- 代码简洁清晰"""

        result = self.cot(SYSTEM_PROMPT, user_prompt)

        # 清理：去掉可能的 markdown 代码块包裹
        code = result.strip()
        if code.startswith("```"):
            code = code.split("\n", 1)[1] if "\n" in code else code[3:]
            code = code.rsplit("```", 1)[0]
        code = code.strip()

        # 确保第一行是图表类型声明
        first_line = code.split("\n")[0].strip().lower()
        valid_types = ["flowchart", "sequencediagram", "classdiagram",
                       "statediagram", "erdiagram", "graph", "gantt", "pie"]
        if not any(first_line.startswith(t) for t in valid_types):
            # 如果 LLM 输出了多余内容，尝试提取代码块
            match = re.search(r"((?:flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|graph|gantt|pie)\b.*)",
                              code, re.DOTALL | re.IGNORECASE)
            if match:
                code = match.group(1).strip()

        return code
