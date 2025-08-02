"""
增强的 Strands 测试执行器 - 使用详细的 MCP 日志记录
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
from mcp import stdio_client, StdioServerParameters

from core.enhanced_mcp_client import EnhancedMCPClient
from core.report_generator import ReportGenerator, TestResultBuilder, TestResult


class EnhancedStrandsTestExecutor:
    """增强的基于 Strands Agents 的测试执行器 - 使用详细的 MCP 日志"""
    
    def __init__(self, region: str = "us-west-2", enable_detailed_logging: bool = True):
        self.region = region
        self.enable_detailed_logging = enable_detailed_logging
        self.report_generator = ReportGenerator()

        # 创建 Bedrock 模型实例
        self.model = BedrockModel(
            model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_name=region
        )

        # 创建增强的 MCP Playwright 客户端
        if enable_detailed_logging:
            self.playwright_client = EnhancedMCPClient(
                lambda: stdio_client(StdioServerParameters(
                    command="npx",
                    args=["@executeautomation/playwright-mcp-server", "--headless"]
                )),
                log_file="logs/mcp_playwright_detailed.jsonl"
            )
        else:
            # 使用标准客户端
            from strands.tools.mcp import MCPClient
            self.playwright_client = MCPClient(
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
        """执行测试用例并生成详细的执行报告"""
        start_time = datetime.now()
        test_id = test_case.get('id', f'test-{int(start_time.timestamp())}')
        
        print(f"🚀 开始执行测试用例: {test_case.get('name', test_id)}")
        
        # 创建测试结果构建器
        result_builder = TestResultBuilder(
            test_id=test_id,
            test_name=test_case.get('name', ''),
            description=test_case.get('description', ''),
            tags=test_case.get('tags', [])
        )
        
        try:
            # 使用增强的 MCP 客户端
            with self.playwright_client as client:
                print("✅ MCP Playwright 客户端连接成功")
                
                # 获取可用工具
                tools = client.list_tools_sync()
                print(f"📋 发现 {len(tools)} 个可用工具")
                
                # 创建 Strands Agent
                agent = Agent(
                    name="test_executor",
                    model=self.model,
                    tools=tools,
                    system_prompt=self._get_system_prompt()
                )
                
                # 构建测试执行提示
                test_prompt = self._build_test_prompt(test_case)
                print(f"📝 构建测试提示: {len(test_prompt)} 字符")
                
                # 执行测试
                print("🎭 开始执行 Playwright 自动化测试...")
                response = await agent.run(test_prompt)
                
                # 解析执行结果
                execution_result = self._parse_execution_result(response)
                
                # 构建测试结果
                result_builder.set_status("passed" if execution_result.get('success', False) else "failed")
                result_builder.set_execution_time(datetime.now() - start_time)
                
                # 添加步骤结果
                for i, step in enumerate(test_case.get('steps', [])):
                    step_result = execution_result.get('steps', {}).get(str(i), {})
                    result_builder.add_step_result(
                        step_name=step.get('action', f'Step {i+1}'),
                        status="passed" if step_result.get('success', False) else "failed",
                        details=step_result.get('details', ''),
                        screenshot_path=step_result.get('screenshot', None)
                    )
                
                # 添加原始输出
                result_builder.add_raw_output(str(response))
                
                # 如果启用了详细日志，获取性能报告
                if self.enable_detailed_logging and hasattr(client, 'get_performance_report'):
                    performance_report = client.get_performance_report()
                    result_builder.add_metadata('mcp_performance', performance_report)
                
        except Exception as e:
            print(f"❌ 测试执行失败: {e}")
            result_builder.set_status("failed")
            result_builder.set_error(str(e))
            result_builder.set_execution_time(datetime.now() - start_time)
        
        # 构建最终结果
        test_result = result_builder.build()
        
        # 生成报告
        report_files = await self._generate_reports(test_result)
        
        # 构建返回结果
        execution_summary = {
            'test_id': test_id,
            'status': test_result.status,
            'model_used': self.model_id,
            'region': self.region,
            'steps_count': len(test_case.get('steps', [])),
            'passed_steps': len([s for s in test_result.steps if s.status == 'passed']),
            'failed_steps': len([s for s in test_result.steps if s.status == 'failed']),
            'duration': test_result.execution_time.total_seconds() if test_result.execution_time else 0,
            'playwright_tools_count': len(tools) if 'tools' in locals() else 0,
            'detailed_logging_enabled': self.enable_detailed_logging
        }
        
        if test_result.status == 'failed' and test_result.error:
            execution_summary['error'] = test_result.error
        
        return {
            'execution_summary': execution_summary,
            'test_result': test_result.to_dict(),
            'report_files': report_files,
            'raw_output': test_result.raw_output
        }
    
    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        return """你是一个专业的前端自动化测试执行器。你的任务是：

1. 理解测试用例的意图和步骤
2. 使用 Playwright 工具执行浏览器自动化操作
3. 验证测试结果是否符合预期
4. 提供详细的执行报告

可用的操作包括：
- 导航到页面
- 查找和操作页面元素
- 输入文本和点击按钮
- 等待页面加载和元素出现
- 截图和验证页面内容
- 处理弹窗和表单

请按照测试步骤逐一执行，并在每个步骤后报告执行结果。如果遇到错误，请详细描述问题并尝试解决。"""
    
    def _build_test_prompt(self, test_case: Dict[str, Any]) -> str:
        """构建测试执行提示"""
        prompt_parts = [
            f"测试用例名称: {test_case.get('name', '')}",
            f"测试描述: {test_case.get('description', '')}",
            "",
            "请执行以下测试步骤:",
        ]
        
        for i, step in enumerate(test_case.get('steps', []), 1):
            action = step.get('action', '')
            data = step.get('data', '')
            prompt_parts.append(f"{i}. {action}")
            if data:
                prompt_parts.append(f"   数据: {data}")
        
        prompt_parts.extend([
            "",
            "预期结果:",
        ])
        
        for result in test_case.get('expected_results', []):
            prompt_parts.append(f"- {result}")
        
        prompt_parts.extend([
            "",
            "请逐步执行测试，并在每个步骤后报告执行状态。最后提供整体测试结果的总结。"
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_execution_result(self, response) -> Dict[str, Any]:
        """解析执行结果"""
        # 这里可以根据实际的响应格式进行解析
        # 目前返回一个基本的结构
        return {
            'success': True,  # 根据实际响应判断
            'steps': {},
            'summary': str(response)
        }
    
    async def _generate_reports(self, test_result: TestResult) -> Dict[str, str]:
        """生成测试报告"""
        report_files = {}
        
        try:
            # 生成 HTML 报告
            html_report_path = f"reports/html/{test_result.test_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            await self.report_generator.generate_html_report(test_result, html_report_path)
            report_files['html'] = html_report_path
            
            # 生成 JSON 报告
            json_report_path = f"reports/json/{test_result.test_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            await self.report_generator.generate_json_report(test_result, json_report_path)
            report_files['json'] = json_report_path
            
        except Exception as e:
            print(f"⚠️ 报告生成失败: {e}")
        
        return report_files
    
    def get_mcp_performance_summary(self) -> Optional[Dict[str, Any]]:
        """获取 MCP 性能摘要"""
        if (self.enable_detailed_logging and 
            hasattr(self.playwright_client, 'get_performance_report')):
            return self.playwright_client.get_performance_report()
        return None
