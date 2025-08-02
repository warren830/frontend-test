"""
测试报告生成器
支持多种报告格式：HTML、JSON、Allure等
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from jinja2 import Template
import base64

@dataclass
class TestStep:
    """测试步骤"""
    name: str
    description: str
    status: str  # passed, failed, skipped
    duration: float
    screenshot: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    test_name: str
    test_description: str
    status: str  # passed, failed, skipped
    start_time: str
    end_time: str
    duration: float
    steps: List[TestStep]
    error_message: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

class ReportGenerator:
    """测试报告生成器"""
    
    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 创建子目录
        (self.output_dir / "html").mkdir(exist_ok=True)
        (self.output_dir / "json").mkdir(exist_ok=True)
        (self.output_dir / "allure").mkdir(exist_ok=True)
        (self.output_dir / "screenshots").mkdir(exist_ok=True)
    
    def generate_html_report(self, test_results: List[TestResult]) -> str:
        """生成HTML报告"""
        template_str = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>前端自动化测试报告</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }
        .header h1 { margin: 0; font-size: 2.5em; }
        .header .subtitle { opacity: 0.9; margin-top: 10px; }
        .summary { display: flex; justify-content: space-around; padding: 30px; background: #f8f9fa; }
        .summary-item { text-align: center; }
        .summary-item .number { font-size: 2em; font-weight: bold; margin-bottom: 5px; }
        .summary-item .label { color: #666; text-transform: uppercase; font-size: 0.9em; }
        .passed { color: #28a745; }
        .failed { color: #dc3545; }
        .skipped { color: #ffc107; }
        .test-results { padding: 30px; }
        .test-item { border: 1px solid #e9ecef; border-radius: 6px; margin-bottom: 20px; overflow: hidden; }
        .test-header { padding: 20px; background: #f8f9fa; cursor: pointer; display: flex; justify-content: between; align-items: center; }
        .test-header:hover { background: #e9ecef; }
        .test-title { font-size: 1.2em; font-weight: bold; }
        .test-meta { color: #666; font-size: 0.9em; margin-top: 5px; }
        .test-status { padding: 4px 12px; border-radius: 20px; color: white; font-size: 0.8em; font-weight: bold; }
        .test-details { padding: 20px; display: none; }
        .test-details.show { display: block; }
        .steps { margin-top: 20px; }
        .step { border-left: 3px solid #e9ecef; padding: 15px; margin-bottom: 10px; background: #f8f9fa; }
        .step.passed { border-left-color: #28a745; }
        .step.failed { border-left-color: #dc3545; }
        .step.skipped { border-left-color: #ffc107; }
        .step-header { font-weight: bold; margin-bottom: 8px; }
        .step-description { color: #666; margin-bottom: 8px; }
        .step-meta { font-size: 0.8em; color: #999; }
        .error-message { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 4px; margin-top: 10px; }
        .screenshot { margin-top: 10px; }
        .screenshot img { max-width: 100%; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .tags { margin-top: 10px; }
        .tag { background: #007bff; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin-right: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>前端自动化测试报告</h1>
            <div class="subtitle">生成时间: {{ report_time }}</div>
        </div>
        
        <div class="summary">
            <div class="summary-item">
                <div class="number">{{ total_tests }}</div>
                <div class="label">总测试数</div>
            </div>
            <div class="summary-item">
                <div class="number passed">{{ passed_tests }}</div>
                <div class="label">通过</div>
            </div>
            <div class="summary-item">
                <div class="number failed">{{ failed_tests }}</div>
                <div class="label">失败</div>
            </div>
            <div class="summary-item">
                <div class="number skipped">{{ skipped_tests }}</div>
                <div class="label">跳过</div>
            </div>
            <div class="summary-item">
                <div class="number">{{ success_rate }}%</div>
                <div class="label">成功率</div>
            </div>
        </div>
        
        <div class="test-results">
            <h2>测试结果详情</h2>
            {% for test in test_results %}
            <div class="test-item">
                <div class="test-header" onclick="toggleDetails('test-{{ loop.index }}')">
                    <div>
                        <div class="test-title">{{ test.test_name }}</div>
                        <div class="test-meta">
                            {{ test.test_description }} | 
                            执行时间: {{ "%.2f"|format(test.duration) }}s |
                            开始时间: {{ test.start_time }}
                        </div>
                        {% if test.tags %}
                        <div class="tags">
                            {% for tag in test.tags %}
                            <span class="tag">{{ tag }}</span>
                            {% endfor %}
                        </div>
                        {% endif %}
                    </div>
                    <div class="test-status {{ test.status }}">{{ test.status.upper() }}</div>
                </div>
                <div class="test-details" id="test-{{ loop.index }}">
                    {% if test.error_message %}
                    <div class="error-message">
                        <strong>错误信息:</strong><br>
                        {{ test.error_message }}
                    </div>
                    {% endif %}
                    
                    <div class="steps">
                        <h4>执行步骤:</h4>
                        {% for step in test.steps %}
                        <div class="step {{ step.status }}">
                            <div class="step-header">{{ step.name }}</div>
                            <div class="step-description">{{ step.description }}</div>
                            <div class="step-meta">
                                状态: {{ step.status.upper() }} | 
                                耗时: {{ "%.2f"|format(step.duration) }}s |
                                时间: {{ step.timestamp }}
                            </div>
                            {% if step.error_message %}
                            <div class="error-message">{{ step.error_message }}</div>
                            {% endif %}
                            {% if step.screenshot %}
                            <div class="screenshot">
                                <img src="data:image/png;base64,{{ step.screenshot }}" alt="步骤截图">
                            </div>
                            {% endif %}
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <script>
        function toggleDetails(id) {
            const element = document.getElementById(id);
            element.classList.toggle('show');
        }
    </script>
</body>
</html>
        """
        
        # 计算统计信息
        total_tests = len(test_results)
        passed_tests = sum(1 for t in test_results if t.status == 'passed')
        failed_tests = sum(1 for t in test_results if t.status == 'failed')
        skipped_tests = sum(1 for t in test_results if t.status == 'skipped')
        success_rate = round((passed_tests / total_tests * 100) if total_tests > 0 else 0, 1)
        
        template = Template(template_str)
        html_content = template.render(
            test_results=test_results,
            report_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            success_rate=success_rate
        )
        
        # 保存HTML报告
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_file = self.output_dir / "html" / f"test_report_{timestamp}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(html_file)
    
    def generate_json_report(self, test_results: List[TestResult]) -> str:
        """生成JSON报告"""
        report_data = {
            "report_info": {
                "generated_at": datetime.now().isoformat(),
                "total_tests": len(test_results),
                "passed": sum(1 for t in test_results if t.status == 'passed'),
                "failed": sum(1 for t in test_results if t.status == 'failed'),
                "skipped": sum(1 for t in test_results if t.status == 'skipped'),
            },
            "test_results": [asdict(test) for test in test_results]
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = self.output_dir / "json" / f"test_report_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return str(json_file)
    
    def generate_allure_report(self, test_results: List[TestResult]) -> str:
        """生成Allure兼容的JSON报告"""
        allure_results = []
        
        for test in test_results:
            # 转换状态
            status_map = {
                'passed': 'passed',
                'failed': 'failed', 
                'skipped': 'skipped'
            }
            
            allure_result = {
                "uuid": str(uuid.uuid4()),
                "name": test.test_name,
                "fullName": f"{test.test_name}#{test.test_id}",
                "description": test.test_description,
                "status": status_map.get(test.status, 'unknown'),
                "start": int(datetime.fromisoformat(test.start_time).timestamp() * 1000),
                "stop": int(datetime.fromisoformat(test.end_time).timestamp() * 1000),
                "labels": [
                    {"name": "suite", "value": "Frontend Tests"},
                    {"name": "testClass", "value": "AutomationTest"},
                    {"name": "testMethod", "value": test.test_name}
                ] + [{"name": "tag", "value": tag} for tag in test.tags],
                "steps": []
            }
            
            # 添加测试步骤
            for step in test.steps:
                allure_step = {
                    "name": step.name,
                    "status": status_map.get(step.status, 'unknown'),
                    "start": int(datetime.fromisoformat(step.timestamp).timestamp() * 1000),
                    "stop": int((datetime.fromisoformat(step.timestamp).timestamp() + step.duration) * 1000),
                    "attachments": []
                }
                
                # 添加截图附件
                if step.screenshot:
                    attachment_uuid = str(uuid.uuid4())
                    allure_step["attachments"].append({
                        "name": "Screenshot",
                        "source": f"{attachment_uuid}-attachment.png",
                        "type": "image/png"
                    })
                    
                    # 保存截图文件
                    screenshot_data = base64.b64decode(step.screenshot)
                    screenshot_file = self.output_dir / "allure" / f"{attachment_uuid}-attachment.png"
                    with open(screenshot_file, 'wb') as f:
                        f.write(screenshot_data)
                
                allure_result["steps"].append(allure_step)
            
            # 添加错误信息
            if test.error_message:
                allure_result["statusDetails"] = {
                    "message": test.error_message,
                    "trace": test.error_message
                }
            
            allure_results.append(allure_result)
        
        # 保存Allure结果文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        for i, result in enumerate(allure_results):
            allure_file = self.output_dir / "allure" / f"{result['uuid']}-result.json"
            with open(allure_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        
        return str(self.output_dir / "allure")
    
    def generate_summary_report(self, test_results: List[TestResult]) -> Dict[str, Any]:
        """生成汇总报告"""
        if not test_results:
            return {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "success_rate": 0,
                "total_duration": 0,
                "average_duration": 0
            }
        
        total_tests = len(test_results)
        passed = sum(1 for t in test_results if t.status == 'passed')
        failed = sum(1 for t in test_results if t.status == 'failed')
        skipped = sum(1 for t in test_results if t.status == 'skipped')
        total_duration = sum(t.duration for t in test_results)
        
        return {
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "success_rate": round((passed / total_tests * 100) if total_tests > 0 else 0, 2),
            "total_duration": round(total_duration, 2),
            "average_duration": round(total_duration / total_tests if total_tests > 0 else 0, 2),
            "generated_at": datetime.now().isoformat()
        }
    
    def save_screenshot(self, screenshot_data: bytes, test_id: str, step_name: str) -> str:
        """保存截图并返回base64编码"""
        # 保存原始截图文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_file = self.output_dir / "screenshots" / f"{test_id}_{step_name}_{timestamp}.png"
        
        with open(screenshot_file, 'wb') as f:
            f.write(screenshot_data)
        
        # 返回base64编码用于HTML报告
        return base64.b64encode(screenshot_data).decode('utf-8')

class TestResultBuilder:
    """测试结果构建器"""
    
    def __init__(self, test_id: str, test_name: str, test_description: str = ""):
        self.test_id = test_id
        self.test_name = test_name
        self.test_description = test_description
        self.start_time = datetime.now()
        self.steps: List[TestStep] = []
        self.tags: List[str] = []
        self.error_message: Optional[str] = None
        self.status = "passed"
    
    def add_step(self, name: str, description: str, duration: float = 0, 
                 status: str = "passed", screenshot: Optional[str] = None, 
                 error_message: Optional[str] = None) -> 'TestResultBuilder':
        """添加测试步骤"""
        step = TestStep(
            name=name,
            description=description,
            status=status,
            duration=duration,
            screenshot=screenshot,
            error_message=error_message
        )
        self.steps.append(step)
        
        # 更新整体测试状态
        if status == "failed":
            self.status = "failed"
        elif status == "skipped" and self.status != "failed":
            self.status = "skipped"
        
        return self
    
    def add_tag(self, tag: str) -> 'TestResultBuilder':
        """添加标签"""
        if tag not in self.tags:
            self.tags.append(tag)
        return self
    
    def set_error(self, error_message: str) -> 'TestResultBuilder':
        """设置错误信息"""
        self.error_message = error_message
        self.status = "failed"
        return self
    
    def build(self) -> TestResult:
        """构建测试结果"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        return TestResult(
            test_id=self.test_id,
            test_name=self.test_name,
            test_description=self.test_description,
            status=self.status,
            start_time=self.start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration=duration,
            steps=self.steps,
            error_message=self.error_message,
            tags=self.tags
        )
