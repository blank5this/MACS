"""Agent 模板注册表 - 支持批量生产 Agent

模板系统允许定义可复用的 Agent 配置模板，通过变量插值和覆盖机制
实现同构 Agent 的批量生产。
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from macs_pkg.core.agent import BaseAgent

# 运行时导入 AgentRole（dataclass 字段和 runtime 比较都需要）
from macs_pkg.core.agent import AgentRole

logger = logging.getLogger(__name__)

# 匹配 {{variable}} 占位符
_PLACEHOLDER_PATTERN = re.compile(r"\{\{([^}]+)\}\}")


@dataclass
class AgentTemplate:
    """Agent 模板定义

    模板包含 Agent 的角色、系统提示词（支持变量插值）、默认模型和工具集。
    通过 render_prompt() 渲染变量，通过 create_agent() 实例化 Agent。

    模板必填字段在 __post_init__ 中校验。

    示例:
        template = AgentTemplate(
            name="erp_planner",
            role=AgentRole.PLANNER,
            system_prompt_template="为项目 {{project_name}} 规划 {{task}}",
            model="gpt-4",
        )
        agent = template.create_agent(
            variables={"project_name": "MACS", "task": "用户认证"},
        )
    """

    name: str
    role: AgentRole
    system_prompt_template: str
    model: str = "gpt-4"
    tools: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """校验必填字段"""
        if not self.name or not self.name.strip():
            raise ValueError("AgentTemplate.name cannot be empty")
        if not self.system_prompt_template or not self.system_prompt_template.strip():
            raise ValueError(f"AgentTemplate[{self.name}].system_prompt_template cannot be empty")
        if self.role is None:
            raise ValueError(f"AgentTemplate[{self.name}].role cannot be None")
        # tools 元素类型校验
        for t in self.tools:
            if not isinstance(t, str):
                raise TypeError(
                    f"AgentTemplate[{self.name}].tools must contain str, got {type(t).__name__}"
                )

    def get_required_variables(self) -> List[str]:
        """从模板提示词中提取所有 {{variable}} 占位符变量名"""
        return _PLACEHOLDER_PATTERN.findall(self.system_prompt_template)

    def render_prompt(
        self, variables: Optional[Dict[str, str]] = None
    ) -> str:
        """将系统提示词模板中的 {{variable}} 占位符替换为实际值

        Args:
            variables: 变量名到值的映射，如 {"project_name": "MACS"}

        Returns:
            渲染后的提示词字符串

        Raises:
            ValueError: variables 为 None（调用方必须显式传 {}）
        """
        if variables is None:
            raise ValueError(
                "variables cannot be None; pass {} if no variables are needed"
            )

        prompt = self.system_prompt_template

        # 检测未填充的占位符并记录警告
        remaining_placeholders = _PLACEHOLDER_PATTERN.findall(prompt)
        if remaining_placeholders:
            unbound = [v for v in remaining_placeholders if v not in variables]
            if unbound:
                unbound_display = unbound[0] if len(unbound) == 1 else unbound
                logger.warning(
                    "AgentTemplate[%s] render_prompt: unbound variables %s, "
                    "provided variables: %s",
                    self.name, unbound_display, list(variables.keys()),
                )

        for key, value in variables.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", value)

        return prompt

    def create_agent(
        self,
        variables: Optional[Dict[str, str]] = None,
        overrides: Optional[Dict[str, Any]] = None,
        provider: Optional[Any] = None,
    ) -> BaseAgent:
        """从模板创建 Agent 实例

        Args:
            variables: 提示词变量映射；为 None 时不执行渲染
            overrides: 覆盖模板的默认配置，支持 name(str) / model(str)
            provider: LLM Provider 实例

        Returns:
            BaseAgent 子类实例

        Raises:
            ValueError: variables 为 None
            TypeError: overrides 中 name/model 类型不是 str
        """
        variables = variables or {}
        overrides = overrides or {}

        # 校验 overrides 类型
        if "name" in overrides and not isinstance(overrides["name"], str):
            raise TypeError(
                f"overrides['name'] must be str, got {type(overrides['name']).__name__}"
            )
        if "model" in overrides and not isinstance(overrides["model"], str):
            raise TypeError(
                f"overrides['model'] must be str, got {type(overrides['model']).__name__}"
            )

        rendered_prompt = self.render_prompt(variables)
        agent_name = overrides.get("name", self.name)
        agent_model = overrides.get("model", self.model)

        # 根据 role + provider 选择 Agent 类
        # 有 provider 时使用 LLM-powered 版本（带有 SYSTEM_PROMPT 类变量）
        # 无 provider 时使用基础 Agent（接受 system_prompt 参数）
        if self.role == AgentRole.PLANNER:
            from macs_pkg.agents.planner import PlannerAgent
            if provider is not None:
                try:
                    from macs_pkg.llm.agents import LLMPlannerAgent
                    agent_cls = LLMPlannerAgent
                    use_llm_agent = True
                except ImportError:
                    agent_cls = PlannerAgent
                    use_llm_agent = False
            else:
                agent_cls = PlannerAgent
                use_llm_agent = False
        elif self.role == AgentRole.EXECUTOR:
            from macs_pkg.agents.executor import ExecutorAgent
            if provider is not None:
                try:
                    from macs_pkg.llm.agents import LLMExecutorAgent
                    agent_cls = LLMExecutorAgent
                    use_llm_agent = True
                except ImportError:
                    agent_cls = ExecutorAgent
                    use_llm_agent = False
            else:
                agent_cls = ExecutorAgent
                use_llm_agent = False
        elif self.role == AgentRole.REVIEWER:
            from macs_pkg.agents.reviewer import ReviewerAgent
            if provider is not None:
                try:
                    from macs_pkg.llm.agents import LLMReviewerAgent
                    agent_cls = LLMReviewerAgent
                    use_llm_agent = True
                except ImportError:
                    agent_cls = ReviewerAgent
                    use_llm_agent = False
            else:
                agent_cls = ReviewerAgent
                use_llm_agent = False
        elif self.role == AgentRole.TOOL:
            from macs_pkg.agents.tool_agent import ToolAgent
            agent_cls = ToolAgent
            use_llm_agent = False
        else:
            from macs_pkg.core.agent import SimpleAgent
            agent_cls = SimpleAgent
            use_llm_agent = False

        # LLM-powered agents define SYSTEM_PROMPT as class variable and do NOT accept
        # system_prompt in __init__ (it's hardcoded), so we don't pass it.
        # Plain agents accept system_prompt as a parameter.
        if use_llm_agent:
            return agent_cls(
                name=agent_name,
                model=agent_model,
                provider=provider,
            )
        else:
            return agent_cls(
                name=agent_name,
                model=agent_model,
                system_prompt=rendered_prompt,
                provider=provider,
            )


@dataclass
class AgentTemplateConfig:
    """模板配置数据类（用于从 dict 或 YAML 加载）"""

    name: str
    role: str  # "planner" | "executor" | "reviewer" | "tool"
    system_prompt: str
    model: Optional[str] = None
    tools: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("AgentTemplateConfig.name cannot be empty")
        if not self.system_prompt or not self.system_prompt.strip():
            raise ValueError(f"AgentTemplateConfig[{self.name}].system_prompt cannot be empty")
        if self.role not in ("planner", "executor", "reviewer", "tool"):
            raise ValueError(
                f"AgentTemplateConfig[{self.name}].role must be one of "
                "planner/executor/reviewer/tool, got '{self.role}'"
            )


class AgentTemplateRegistry:
    """Agent 模板注册表（线程安全单例）

    提供模板的注册、查询、批量创建功能。

    示例:
        registry = AgentTemplateRegistry.get_instance()

        # 注册模板（不允许覆盖已有模板）
        registry.register(AgentTemplate(
            name="erp_expert",
            role=AgentRole.EXECUTOR,
            system_prompt_template="你是 {{domain}} 专家...",
        ))

        # 从模板创建 Agent
        agent = registry.create_agent(
            "erp_expert",
            variables={"domain": "财务"},
            overrides={"name": "finance_expert"},
        )

        # 批量创建
        agents = registry.batch_create([
            {"template": "erp_expert", "overrides": {"name": "agent_1"}},
            {"template": "erp_expert", "overrides": {"name": "agent_2"}},
        ])
    """

    _instance: Optional["AgentTemplateRegistry"] = None

    def __new__(cls) -> "AgentTemplateRegistry":
        """线程安全单例：使用 __new__ 而非 __init__ 防重入"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 初始化单例实例
            cls._instance.__init_registry()
        return cls._instance

    def __init_registry(self) -> None:
        """单例初始化（仅调用一次）"""
        self._templates: Dict[str, AgentTemplate] = {}
        self._init_builtin_templates()

    # 禁止外部调用 __init__（单例模式）
    def __init__(self) -> None:
        # 不在这里做初始化；如果 __new__ 已初始化，这里直接返回
        # 这是防御性编程，防止意外调用破坏单例
        pass

    def _init_builtin_templates(self) -> None:
        """初始化内置模板"""
        from macs_pkg.core.agent import AgentRole

        builtin_specs = [
            AgentTemplate(
                name="default_planner",
                role=AgentRole.PLANNER,
                system_prompt_template="""你是一个任务规划专家。
你的职责是将用户请求分解为可执行的子任务序列。

当前项目: {{project_name}}
可用工具: {{available_tools}}

用户请求: {{task}}

请将上述请求分解为具体的子任务，每个子任务应该:
1. 描述清晰的目标
2. 可独立执行
3. 有明确的完成标准

输出格式:
- 子任务编号
- 子任务描述
- 预期产出""",
                model="gpt-4",
            ),
            AgentTemplate(
                name="default_executor",
                role=AgentRole.EXECUTOR,
                system_prompt_template="""你是一个任务执行专家。
当前项目: {{project_name}}
你的角色: {{agent_role}}

执行任务: {{task}}

{{rag_context}}

请执行上述任务，返回执行结果和任何需要注意的事项。""",
                model="gpt-4",
            ),
            AgentTemplate(
                name="default_reviewer",
                role=AgentRole.REVIEWER,
                system_prompt_template="""你是一个质量审核专家。

审核标准:
{{criteria}}

待审核内容:
{{content}}

请根据审核标准对内容进行审核，返回:
1. 是否通过
2. 发现的问题（如有）
3. 改进建议（如有）""",
                model="gpt-4",
            ),
            AgentTemplate(
                name="erp_knowledge_expert",
                role=AgentRole.EXECUTOR,
                system_prompt_template="""你是一个 ERP 知识专家。
专注于领域: {{domain}}
当前日期: {{current_date}}

请基于以下知识库内容回答用户问题。

{{rag_context}}

用户问题: {{question}}

请提供准确、专业的回答。如果知识库中没有相关信息，请明确告知。""",
                model="gpt-4",
                tools=["erp_knowledge_search"],
            ),
        ]

        for t in builtin_specs:
            # 内置模板直接写入字典，跳过 allow_override 保护
            self._templates[t.name] = t

    def register(
        self, template: AgentTemplate, *, allow_override: bool = False
    ) -> None:
        """注册模板

        Args:
            template: AgentTemplate 实例
            allow_override: 是否允许覆盖已有模板。默认 False（安全优先）

        Raises:
            TypeError: template 不是 AgentTemplate 实例
            ValueError: 已存在同名模板且 allow_override=False
        """
        if not isinstance(template, AgentTemplate):
            raise TypeError(
                f"template must be AgentTemplate, got {type(template).__name__}"
            )
        if template.name in self._templates and not allow_override:
            raise ValueError(
                f"Template '{template.name}' is already registered. "
                "Use allow_override=True to replace it."
            )
        self._templates[template.name] = template

    def get(self, name: str) -> Optional[AgentTemplate]:
        """获取模板

        Args:
            name: 模板名称

        Returns:
            模板实例，不存在则返回 None
        """
        return self._templates.get(name)

    def list_templates(self) -> List[str]:
        """列出所有已注册的模板名称（按注册顺序）"""
        return list(self._templates.keys())

    def create_agent(
        self,
        template_name: str,
        variables: Optional[Dict[str, str]] = None,
        overrides: Optional[Dict[str, Any]] = None,
        provider: Optional[Any] = None,
    ) -> BaseAgent:
        """从模板创建 Agent 实例

        Args:
            template_name: 模板名称
            variables: 提示词变量映射
            overrides: 覆盖模板配置（如 name、model）
            provider: LLM Provider

        Returns:
            BaseAgent 实例

        Raises:
            ValueError: 模板不存在，或 variables 为 None
        """
        template = self.get(template_name)
        if not template:
            available = ", ".join(self.list_templates()) or "(无)"
            raise ValueError(
                f"Template '{template_name}' not found. Available: {available}"
            )
        return template.create_agent(variables, overrides, provider)

    def batch_create(
        self,
        configs: List[Dict[str, Any]],
        provider: Optional[Any] = None,
    ) -> List[BaseAgent]:
        """批量从模板创建 Agent

        config 格式:
            {
                "template": "template_name",      # 必填，模板名称
                "variables": {"key": "value"},   # 可选，提示词变量
                "overrides": {"name": "custom"}   # 可选，覆盖模板配置
            }

        Args:
            configs: 配置列表
            provider: LLM Provider（会传递给每个 Agent）

        Returns:
            创建的 Agent 列表

        Raises:
            ValueError: 任意配置项中 template 字段缺失
        """
        agents = []
        for idx, config in enumerate(configs):
            if "template" not in config:
                raise ValueError(
                    f"batch_create config[{idx}] is missing required field 'template'"
                )
            template_name = config["template"]
            variables = config.get("variables", {})
            overrides = config.get("overrides", {})
            try:
                agent = self.create_agent(template_name, variables, overrides, provider)
                agents.append(agent)
            except ValueError as exc:
                raise ValueError(
                    f"batch_create config[{idx}] failed: {exc}"
                ) from exc
        return agents

    def register_from_config(
        self, config: AgentTemplateConfig, *, allow_override: bool = False
    ) -> None:
        """从 AgentTemplateConfig 注册模板

        Args:
            config: 模板配置
            allow_override: 是否允许覆盖

        Raises:
            ValueError: config.role 无效
        """
        from macs_pkg.core.agent import AgentRole

        try:
            role = AgentRole(config.role)
        except ValueError:
            raise ValueError(
                f"Invalid role '{config.role}' for template '{config.name}'. "
                "Must be one of: planner, executor, reviewer, tool"
            )

        template = AgentTemplate(
            name=config.name,
            role=role,
            system_prompt_template=config.system_prompt,
            model=config.model or "gpt-4",
            tools=config.tools or [],
            metadata=config.metadata,
        )
        self.register(template, allow_override=allow_override)

    def load_from_dicts(
        self, configs: List[Dict[str, Any]], *, allow_override: bool = False
    ) -> None:
        """从字典列表批量注册模板

        Args:
            configs: 配置字典列表
            allow_override: 是否允许覆盖已有模板
        """
        for cfg in configs:
            config = AgentTemplateConfig(**cfg)
            self.register_from_config(config, allow_override=allow_override)

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例（仅用于测试）"""
        cls._instance = None


def get_template_registry() -> AgentTemplateRegistry:
    """获取模板注册表实例的便捷函数"""
    return AgentTemplateRegistry()
