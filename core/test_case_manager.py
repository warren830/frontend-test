"""
测试用例管理器
负责测试用例的创建、存储、加载和管理
"""

import os
import json
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import uuid

class TestCase:
    """测试用例类"""
    
    def __init__(self, name: str, description: str = "", steps: List[Dict] = None, 
                 expected_results: List[str] = None, tags: List[str] = None,
                 priority: str = "medium", test_type: str = "functional"):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.steps = steps or []
        self.expected_results = expected_results or []
        self.tags = tags or []
        self.priority = priority  # low, medium, high, critical
        self.test_type = test_type  # functional, ui, api, performance
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.status = "draft"  # draft, active, deprecated
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": self.steps,
            "expected_results": self.expected_results,
            "tags": self.tags,
            "priority": self.priority,
            "test_type": self.test_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCase':
        """从字典创建测试用例"""
        test_case = cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            steps=data.get("steps", []),
            expected_results=data.get("expected_results", []),
            tags=data.get("tags", []),
            priority=data.get("priority", "medium"),
            test_type=data.get("test_type", "functional")
        )
        test_case.id = data.get("id", test_case.id)
        test_case.created_at = data.get("created_at", test_case.created_at)
        test_case.updated_at = data.get("updated_at", test_case.updated_at)
        test_case.status = data.get("status", "draft")
        return test_case

class TestCaseManager:
    """测试用例管理器"""
    
    def __init__(self, test_cases_dir: str = "test_cases"):
        self.test_cases_dir = Path(test_cases_dir)
        self.test_cases_dir.mkdir(exist_ok=True)
        self.test_cases: Dict[str, TestCase] = {}
        self.load_all_test_cases()
    
    def create_test_case(self, name: str, description: str = "", 
                        steps: List[Dict] = None, expected_results: List[str] = None,
                        tags: List[str] = None, priority: str = "medium", 
                        test_type: str = "functional") -> TestCase:
        """创建新的测试用例"""
        test_case = TestCase(
            name=name,
            description=description,
            steps=steps,
            expected_results=expected_results,
            tags=tags,
            priority=priority,
            test_type=test_type
        )
        self.test_cases[test_case.id] = test_case
        self.save_test_case(test_case)
        return test_case
    
    def _create_test_case_sync(self, name: str, description: str = "", 
                              steps: List[Dict] = None, expected_results: List[str] = None,
                              tags: List[str] = None, priority: str = "medium", 
                              test_type: str = "functional") -> TestCase:
        """同步创建新的测试用例（内部使用）"""
        test_case = TestCase(
            name=name,
            description=description,
            steps=steps,
            expected_results=expected_results,
            tags=tags,
            priority=priority,
            test_type=test_type
        )
        self.test_cases[test_case.id] = test_case
        self.save_test_case(test_case)
        return test_case
    
    async def create_test_case(self, name: str, description: str = "", 
                              steps: List[Dict] = None, expected_results: List[str] = None,
                              tags: List[str] = None, priority: str = "medium", 
                              test_type: str = "functional") -> Dict[str, Any]:
        """异步创建新的测试用例（返回字典格式）"""
        test_case = TestCase(
            name=name,
            description=description,
            steps=steps,
            expected_results=expected_results,
            tags=tags,
            priority=priority,
            test_type=test_type
        )
        self.test_cases[test_case.id] = test_case
        self.save_test_case(test_case)
        return test_case.to_dict()
    
    def save_test_case(self, test_case: TestCase) -> bool:
        """保存测试用例到文件"""
        try:
            file_path = self.test_cases_dir / f"{test_case.id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(test_case.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存测试用例失败: {e}")
            return False
    
    def load_test_case(self, test_case_id: str) -> Optional[TestCase]:
        """加载单个测试用例"""
        try:
            file_path = self.test_cases_dir / f"{test_case_id}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                test_case = TestCase.from_dict(data)
                self.test_cases[test_case.id] = test_case
                return test_case
        except Exception as e:
            print(f"加载测试用例失败: {e}")
        return None
    
    def load_all_test_cases(self) -> None:
        """加载所有测试用例"""
        if not self.test_cases_dir.exists():
            return
            
        for file_path in self.test_cases_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                test_case = TestCase.from_dict(data)
                self.test_cases[test_case.id] = test_case
            except Exception as e:
                print(f"加载测试用例文件 {file_path} 失败: {e}")
    
    def get_test_case(self, test_case_id: str) -> Optional[TestCase]:
        """获取测试用例"""
        return self.test_cases.get(test_case_id)
    
    def get_all_test_cases(self) -> List[TestCase]:
        """获取所有测试用例"""
        return list(self.test_cases.values())
    
    async def list_test_cases(self) -> List[Dict[str, Any]]:
        """异步获取所有测试用例（返回字典格式）"""
        return [tc.to_dict() for tc in self.test_cases.values()]
    
    def get_test_cases_by_tag(self, tag: str) -> List[TestCase]:
        """根据标签获取测试用例"""
        return [tc for tc in self.test_cases.values() if tag in tc.tags]
    
    def get_test_cases_by_type(self, test_type: str) -> List[TestCase]:
        """根据类型获取测试用例"""
        return [tc for tc in self.test_cases.values() if tc.test_type == test_type]
    
    def get_test_cases_by_priority(self, priority: str) -> List[TestCase]:
        """根据优先级获取测试用例"""
        return [tc for tc in self.test_cases.values() if tc.priority == priority]
    
    def update_test_case(self, test_case_id: str, **kwargs) -> bool:
        """更新测试用例"""
        test_case = self.test_cases.get(test_case_id)
        if not test_case:
            return False
        
        for key, value in kwargs.items():
            if hasattr(test_case, key):
                setattr(test_case, key, value)
        
        test_case.updated_at = datetime.now().isoformat()
        return self.save_test_case(test_case)
    
    def delete_test_case(self, test_case_id: str) -> bool:
        """删除测试用例"""
        try:
            if test_case_id in self.test_cases:
                del self.test_cases[test_case_id]
            
            file_path = self.test_cases_dir / f"{test_case_id}.json"
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            print(f"删除测试用例失败: {e}")
            return False
    
    def search_test_cases(self, query: str) -> List[TestCase]:
        """搜索测试用例"""
        query = query.lower()
        results = []
        
        for test_case in self.test_cases.values():
            if (query in test_case.name.lower() or 
                query in test_case.description.lower() or
                any(query in tag.lower() for tag in test_case.tags)):
                results.append(test_case)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取测试用例统计信息"""
        total = len(self.test_cases)
        if total == 0:
            return {
                "total": 0,
                "by_type": {},
                "by_priority": {},
                "by_status": {}
            }
        
        by_type = {}
        by_priority = {}
        by_status = {}
        
        for test_case in self.test_cases.values():
            # 按类型统计
            by_type[test_case.test_type] = by_type.get(test_case.test_type, 0) + 1
            # 按优先级统计
            by_priority[test_case.priority] = by_priority.get(test_case.priority, 0) + 1
            # 按状态统计
            by_status[test_case.status] = by_status.get(test_case.status, 0) + 1
        
        return {
            "total": total,
            "by_type": by_type,
            "by_priority": by_priority,
            "by_status": by_status
        }
    
    def export_test_cases(self, format: str = "json") -> str:
        """导出测试用例"""
        data = [tc.to_dict() for tc in self.test_cases.values()]
        
        if format.lower() == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif format.lower() == "yaml":
            return yaml.dump(data, allow_unicode=True, default_flow_style=False)
        else:
            raise ValueError(f"不支持的导出格式: {format}")
    
    def import_test_cases(self, data: str, format: str = "json") -> int:
        """导入测试用例"""
        try:
            if format.lower() == "json":
                test_cases_data = json.loads(data)
            elif format.lower() == "yaml":
                test_cases_data = yaml.safe_load(data)
            else:
                raise ValueError(f"不支持的导入格式: {format}")
            
            imported_count = 0
            for tc_data in test_cases_data:
                test_case = TestCase.from_dict(tc_data)
                self.test_cases[test_case.id] = test_case
                if self.save_test_case(test_case):
                    imported_count += 1
            
            return imported_count
        except Exception as e:
            print(f"导入测试用例失败: {e}")
            return 0
    
    def create_sample_test_cases(self) -> None:
        """创建示例测试用例"""
        sample_cases = [
            {
                "name": "登录功能测试",
                "description": "测试用户登录功能的正常流程",
                "steps": [
                    {"action": "打开登录页面", "data": "https://example.com/login"},
                    {"action": "输入用户名", "data": "testuser"},
                    {"action": "输入密码", "data": "password123"},
                    {"action": "点击登录按钮", "data": ""}
                ],
                "expected_results": ["成功跳转到首页", "显示用户名"],
                "tags": ["登录", "基础功能"],
                "priority": "high",
                "test_type": "functional"
            },
            {
                "name": "搜索功能测试",
                "description": "测试搜索功能的基本操作",
                "steps": [
                    {"action": "打开首页", "data": "https://example.com"},
                    {"action": "在搜索框输入关键词", "data": "测试"},
                    {"action": "点击搜索按钮", "data": ""}
                ],
                "expected_results": ["显示搜索结果", "结果包含关键词"],
                "tags": ["搜索", "基础功能"],
                "priority": "medium",
                "test_type": "functional"
            },
            {
                "name": "页面响应性测试",
                "description": "测试页面在不同设备上的响应性",
                "steps": [
                    {"action": "打开页面", "data": "https://example.com"},
                    {"action": "调整浏览器窗口大小", "data": "mobile"},
                    {"action": "检查页面布局", "data": ""}
                ],
                "expected_results": ["页面布局适应移动端", "所有元素可见"],
                "tags": ["响应式", "UI"],
                "priority": "medium",
                "test_type": "ui"
            }
        ]
        
        for case_data in sample_cases:
            self._create_test_case_sync(**case_data)
