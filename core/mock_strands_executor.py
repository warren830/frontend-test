"""
模拟版本的 Strands 测试执行器 - 用于演示和测试
"""

import json
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from core.report_generator import ReportGenerator, TestResultBuilder, TestResult

class MockStrandsTestExecutor:
    """模拟版本的 Strands 测试执行器"""
    
    def __init__(self, region: str = "us-west-2"):
        self.region = region
        self.report_generator = ReportGenerator()
        self.model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    async def execute_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个测试用例并生成报告（模拟版本）"""
        result_builder = TestResultBuilder(
            test_id=test_case['id'],
            test_name=test_case['name'],
            test_description=test_case.get('description', '')
        )
        
        # 添加标签
        result_builder.add_tag("automated").add_tag("frontend").add_tag("strands").add_tag("mock")
        if 'tags' in test_case:
            for tag in test_case['tags']:
                result_builder.add_tag(tag)
        
        try:
            print(f"开始执行测试用例: {test_case['name']}")
            print("使用 Mock Strands Agents + AWS Bedrock Claude 3.5 Sonnet")
            
            # 模拟执行延迟
            await asyncio.sleep(1)
            
            # 生成模拟的执行结果
            raw_result = self._generate_mock_result(test_case)
            
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
                    "model_used": "Mock Strands Agents + AWS Bedrock Claude 3.5 Sonnet",
                    "region": self.region
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
                    "model_used": "Mock Strands Agents + AWS Bedrock Claude 3.5 Sonnet",
                    "region": self.region
                }
            }

    def _generate_mock_result(self, test_case: Dict[str, Any]) -> str:
        """生成模拟的测试执行结果"""
        steps = test_case.get('steps', [])
        
        result = """=== 测试执行报告 ===
测试状态: PASSED
总执行时间: 2.35秒
执行摘要: 成功执行了所有测试步骤，达到了预期结果

=== 步骤执行详情 ==="""
        
        for i, step in enumerate(steps, 1):
            if isinstance(step, dict):
                action = step.get('action', '未知操作')
                data = step.get('data', '')
                step_name = f"{action}: {data}" if data else action
            else:
                step_name = str(step)
            
            # 模拟执行时间
            exec_time = round(0.5 + (i * 0.3), 2)
            
            result += f"""
步骤{i}: {step_name}
状态: PASSED
执行时间: {exec_time}秒
描述: 使用自动化工具成功执行了该步骤
结果: 操作成功完成，页面响应正常
错误信息: 无
---"""
        
        expected_results = test_case.get('expected_results', [])
        expected_text = "达到预期结果" if expected_results else "无特定预期结果"
        
        result += f"""

=== 最终验证 ===
预期结果验证: PASSED
验证详情: {expected_text}，所有测试步骤都成功执行

=== 执行总结 ===
本次测试执行非常成功。所有步骤都按预期完成，没有遇到任何错误。
页面响应良好，用户交互流畅。测试结果表明功能运行正常。
"""
        
        return result

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
            result_builder.add_step(
                name="测试执行",
                description="自动化测试执行",
                status="passed",
                duration=1.0
            )

    def _parse_step_details(self, raw_result: str, result_builder: TestResultBuilder):
        """解析步骤详情"""
        # 查找步骤执行详情部分
        steps_match = re.search(r'=== 步骤执行详情 ===(.*?)=== 最终验证 ===', raw_result, re.DOTALL)
        if not steps_match:
            # 如果没有找到步骤详情，添加一个默认步骤
            result_builder.add_step(
                name="测试执行",
                description="执行自动化测试",
                status="passed",
                duration=1.0
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
            
            # 提取描述
            desc_match = re.search(r'描述:\s*(.+)', block)
            if desc_match:
                step_description = desc_match.group(1).strip()
            
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
                "model_used": "Mock Strands Agents + AWS Bedrock Claude 3.5 Sonnet",
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
        
        # 读取所有JSON报告文件（包括 mock 和普通的报告文件）
        for json_file in sorted(reports_dir.glob("*test_report_*.json"), reverse=True):
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
