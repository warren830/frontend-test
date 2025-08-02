"""
基于 Strands Agents 的测试执行器 - 集成 MCP Playwright
"""

import json
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import strands
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters

from core.report_generator import ReportGenerator, TestResultBuilder, TestResult

class StrandsTestExecutor:
    """基于 Strands Agents 的测试执行器 - 使用 MCP Playwright"""
    
    def __init__(self, region: str = "us-west-2"):
        self.region = region
        self.report_generator = ReportGenerator()

        # 创建 Bedrock 模型实例 - 使用 Claude 3.5 Sonnet
        self.model = BedrockModel(
            model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_name=region
        )

        # 创建 MCP Playwright 客户端
        self.playwright_client = MCPClient(
            # lambda: stdio_client(StdioServerParameters(
            #     command="npx",
            #     args=["@playwright/mcp@latest", "--headless"]
            # ))
            lambda: stdio_client(StdioServerParameters(
                command="npx",
                args=["@executeautomation/playwright-mcp-server", "--headless"]
            ))
        )
    
    @property
    def model_id(self) -> str:
        """获取模型ID"""
        return self.model.config.get('model_id', 'unknown')
    
    async def execute_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个测试用例并生成报告"""
        result_builder = TestResultBuilder(
            test_id=test_case['id'],
            test_name=test_case['name'],
            test_description=test_case.get('description', '')
        )
        
        # 添加标签
        result_builder.add_tag("automated").add_tag("frontend").add_tag("strands").add_tag("playwright")
        if 'tags' in test_case:
            for tag in test_case['tags']:
                result_builder.add_tag(tag)
        
        try:
            # 使用 MCP Playwright 客户端
            with self.playwright_client:
                # 获取 Playwright 工具列表
                playwright_tools = self.playwright_client.list_tools_sync()
                print(f"可用的 Playwright 工具: {[tool.tool_name for tool in playwright_tools]}")
                
                # 创建测试执行代理，使用 Playwright 工具
                agent = Agent(
                    model=self.model,
                    tools=playwright_tools,
                    system_prompt="""你是一个专业的前端自动化测试执行器。
                    你可以使用 Playwright MCP 工具来执行浏览器自动化测试。
                    
                    可用的 Playwright 工具包括页面导航、元素交互、内容获取、截图等功能。
                    
                    执行测试时请：
                    1. 仔细阅读测试用例的每个步骤
                    2. 使用适当的 Playwright 工具来执行每个步骤
                    3. 记录每个步骤的执行结果
                    4. 如果遇到错误，详细记录错误信息
                    5. 最后验证是否达到预期结果
                    
                    请用中文回复，并严格按照要求的格式返回结果。"""
                )
                
                # 构建测试执行指令
                instruction = self._build_test_instruction(test_case)
                
                # 执行测试
                print(f"开始执行测试用例: {test_case['name']}")
                print("使用 Strands Agents + MCP Playwright + AWS Bedrock Claude 3.5 Sonnet")
                
                # 使用 Strands Agent 执行测试（会自动使用 MCP Playwright 工具）
                agent_result = agent(instruction)  # 这返回 AgentResult 对象，不需要 await
                raw_result = str(agent_result)  # 转换为字符串
                
                print(f"测试执行完成，结果长度: {len(raw_result)}")
                
                # 解析执行结果
                self._parse_execution_result(raw_result, result_builder)
                
                # 构建最终测试结果
                test_result = result_builder.build()
                
                # 生成报告
                report_files = await self._generate_reports([test_result])
                
                return {
                    "test_result": test_result,
                    "raw_output": raw_result,
                    "report_files": report_files,
                    "execution_summary": {
                        "status": test_result.status,
                        "duration": test_result.duration,
                        "steps_count": len(test_result.steps),
                        "passed_steps": sum(1 for s in test_result.steps if s.status == 'passed'),
                        "failed_steps": sum(1 for s in test_result.steps if s.status == 'failed'),
                        "model_used": "Strands Agents + MCP Playwright + AWS Bedrock Claude 3.5 Sonnet",
                        "region": self.region,
                        "playwright_tools_count": len(playwright_tools) if playwright_tools else 0
                    }
                }
                    
        except Exception as e:
            print(f"测试执行失败: {e}")
            result_builder.set_error(str(e))
            test_result = result_builder.build()
            
            return {
                "test_result": test_result,
                "raw_output": f"执行失败: {str(e)}",
                "report_files": {},
                "execution_summary": {
                    "status": "failed",
                    "duration": test_result.duration,
                    "steps_count": len(test_result.steps),
                    "passed_steps": 0,
                    "failed_steps": 0,
                    "error": str(e),
                    "model_used": "Strands Agents + MCP Playwright + AWS Bedrock Claude 3.5 Sonnet",
                    "region": self.region
                }
            }

    def _build_test_instruction(self, test_case: Dict[str, Any]) -> str:
        """构建测试执行指令"""
        
        # 格式化预期结果
        expected_results = self._format_expected_results(test_case.get('expected_results', []))
        
        # 格式化测试步骤
        steps_text = self._format_test_steps(test_case.get('steps', []))
        
        instruction = f"""
请使用可用的 Playwright MCP 工具执行以下前端自动化测试用例：

测试用例信息：
- 名称：{test_case['name']}
- 描述：{test_case.get('description', '无描述')}
- ID：{test_case['id']}

测试步骤：
{steps_text}

预期结果：
{expected_results}

执行要求：
1. 首先查看可用的 Playwright 工具，选择合适的工具执行每个步骤
2. 对于导航操作，使用相应的导航工具
3. 对于页面交互（点击、输入），使用相应的交互工具
4. 在关键步骤使用截图工具记录页面状态
5. 使用内容获取工具验证页面内容
6. 记录每个步骤的执行结果和耗时
7. 如果遇到错误，详细记录错误信息并尝试继续执行后续步骤
8. 最后验证是否达到预期结果

请按照以下格式返回结果：

=== 测试执行报告 ===
测试状态: [PASSED/FAILED/ERROR]
总执行时间: [X.XX秒]
执行摘要: [简要描述测试执行情况]

=== 步骤执行详情 ===
步骤1: [步骤名称]
状态: [PASSED/FAILED/SKIPPED]
执行时间: [X.XX秒]
描述: [步骤详细描述]
使用工具: [使用的 Playwright 工具名称]
结果: [实际执行结果]
错误信息: [如有错误，详细描述]
---

步骤2: [步骤名称]
状态: [PASSED/FAILED/SKIPPED]
执行时间: [X.XX秒]
描述: [步骤详细描述]
使用工具: [使用的 Playwright 工具名称]
结果: [实际执行结果]
错误信息: [如有错误，详细描述]
---

=== 最终验证 ===
预期结果验证: [PASSED/FAILED]
验证详情: [详细说明是否达到预期结果]

=== 执行总结 ===
[总结整个测试执行过程，包括成功的操作、遇到的问题、最终结果等]
"""
        
        return instruction

    def _format_expected_results(self, expected_results) -> str:
        """格式化预期结果"""
        if not expected_results:
            return "无特定预期结果"
        
        if isinstance(expected_results, list):
            if len(expected_results) == 1:
                return expected_results[0]
            else:
                return "\n".join([f"- {result}" for result in expected_results])
        else:
            return str(expected_results)

    def _format_test_steps(self, steps: List) -> str:
        """格式化测试步骤"""
        if not steps:
            return "无具体步骤"
        
        formatted_steps = []
        for i, step in enumerate(steps, 1):
            if isinstance(step, dict):
                action = step.get('action', '未知操作')
                data = step.get('data', '')
                
                if data:
                    formatted_steps.append(f"{i}. {action}: {data}")
                else:
                    formatted_steps.append(f"{i}. {action}")
            else:
                formatted_steps.append(f"{i}. {step}")
        
        return "\n".join(formatted_steps)

    def _parse_execution_result(self, raw_result: str, result_builder: TestResultBuilder):
        """解析执行结果"""
        try:
            # 解析总体状态
            if "测试状态: PASSED" in raw_result:
                # 测试通过，状态已经是默认的 "passed"
                pass
            elif "测试状态: FAILED" in raw_result or "测试状态: ERROR" in raw_result:
                result_builder.set_error("测试执行失败")
            
            # 解析步骤详情
            self._parse_step_details(raw_result, result_builder)
            
        except Exception as e:
            print(f"解析执行结果时出错: {e}")
            # 如果解析失败，添加一个通用步骤
            status = "failed" if any(keyword in raw_result.lower() for keyword in ["失败", "错误", "failed", "error"]) else "passed"
            result_builder.add_step(
                name="测试执行",
                description="使用 MCP Playwright 执行自动化测试",
                status=status,
                duration=0
            )

    def _parse_step_details(self, raw_result: str, result_builder: TestResultBuilder):
        """解析步骤详情"""
        # 查找步骤执行详情部分
        steps_match = re.search(r'=== 步骤执行详情 ===(.*?)=== 最终验证 ===', raw_result, re.DOTALL)
        if not steps_match:
            # 如果没有找到步骤详情，添加一个默认步骤
            result_builder.add_step(
                name="测试执行",
                description="使用 MCP Playwright 执行自动化测试",
                status="passed",
                duration=0
            )
            return
        
        steps_text = steps_match.group(1)
        
        # 按 "---" 分割步骤
        step_blocks = re.split(r'---+', steps_text)
        
        for block in step_blocks:
            block = block.strip()
            if not block:
                continue
            
            # 解析步骤信息
            step_name = "未知步骤"
            step_status = "passed"
            step_duration = 0.0
            step_description = ""
            error_message = None
            
            # 提取步骤名称
            name_match = re.search(r'步骤\d+:\s*(.+)', block)
            if name_match:
                step_name = name_match.group(1).strip()
            
            # 提取状态
            status_match = re.search(r'状态:\s*(PASSED|FAILED|SKIPPED)', block)
            if status_match:
                status_text = status_match.group(1)
                step_status = status_text.lower() if status_text.lower() in ['passed', 'failed', 'skipped'] else 'passed'
            
            # 提取执行时间
            time_match = re.search(r'执行时间:\s*([\d.]+)秒', block)
            if time_match:
                try:
                    step_duration = float(time_match.group(1))
                except ValueError:
                    step_duration = 0.0
            
            # 提取描述和使用的工具
            desc_match = re.search(r'描述:\s*(.+)', block)
            tool_match = re.search(r'使用工具:\s*(.+)', block)
            
            if desc_match:
                step_description = desc_match.group(1).strip()
            if tool_match:
                tool_info = tool_match.group(1).strip()
                step_description += f" (使用工具: {tool_info})"
            
            # 提取错误信息
            error_match = re.search(r'错误信息:\s*(.+)', block)
            if error_match:
                error_text = error_match.group(1).strip()
                if error_text and error_text != "无" and error_text != "":
                    error_message = error_text
            
            # 添加步骤到结果构建器
            result_builder.add_step(
                name=step_name,
                description=step_description,
                status=step_status,
                duration=step_duration,
                error_message=error_message
            )

    async def execute_test_suite(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行测试套件"""
        suite_start_time = datetime.now()
        test_results = []
        
        for test_case in test_cases:
            print(f"执行测试用例: {test_case['name']}")
            result = await self.execute_test_case(test_case)
            test_results.append(result['test_result'])
        
        suite_end_time = datetime.now()
        suite_duration = (suite_end_time - suite_start_time).total_seconds()
        
        # 生成套件报告
        report_files = await self._generate_reports(test_results)
        
        # 生成汇总统计
        summary = self.report_generator.generate_summary_report(test_results)
        summary['suite_duration'] = round(suite_duration, 2)
        
        return {
            "test_results": test_results,
            "report_files": report_files,
            "summary": summary,
            "suite_info": {
                "total_tests": len(test_cases),
                "start_time": suite_start_time.isoformat(),
                "end_time": suite_end_time.isoformat(),
                "duration": suite_duration,
                "model_used": "Strands Agents + MCP Playwright + AWS Bedrock Claude 3.5 Sonnet",
                "region": self.region
            }
        }

    async def _generate_reports(self, test_results: List[TestResult]) -> Dict[str, str]:
        """生成测试报告"""
        report_files = {}
        
        try:
            # 生成HTML报告
            html_file_path = self.report_generator.generate_html_report(test_results)
            report_files['html'] = html_file_path
            
            # 生成JSON报告
            json_file_path = self.report_generator.generate_json_report(test_results)
            report_files['json'] = json_file_path
            
        except Exception as e:
            print(f"生成报告时出错: {e}")
        
        return report_files
    
    async def get_test_history(self, test_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取测试历史记录"""
        reports_dir = Path("./reports/json")
        if not reports_dir.exists():
            return []
        
        history = []
        
        # 读取所有JSON报告文件
        for json_file in sorted(reports_dir.glob("test_report_*.json"), reverse=True):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                
                # 处理新的报告格式 {report_info: {...}, test_results: [...]}
                if isinstance(report_data, dict) and 'test_results' in report_data:
                    test_results = report_data['test_results']
                    if isinstance(test_results, list):
                        for test_result in test_results:
                            if test_id is None or test_result.get('test_id') == test_id:
                                history.append(test_result)
                    else:
                        if test_id is None or test_results.get('test_id') == test_id:
                            history.append(test_results)
                
                # 处理旧的报告格式（直接是测试结果列表或单个结果）
                elif isinstance(report_data, list):
                    for test_result in report_data:
                        if test_id is None or test_result.get('test_id') == test_id:
                            history.append(test_result)
                
                elif isinstance(report_data, dict) and 'test_id' in report_data:
                    if test_id is None or report_data.get('test_id') == test_id:
                        history.append(report_data)
                        
            except Exception as e:
                print(f"读取报告文件 {json_file} 时出错: {e}")
                continue
        
        return history
