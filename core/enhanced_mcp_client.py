"""
增强的 MCP 客户端 - 提供详细的日志记录和监控功能
"""

import json
import time
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from strands.tools.mcp import MCPClient
from strands.types.tools import ToolResult


class EnhancedMCPClient(MCPClient):
    """增强的 MCP 客户端，提供详细的日志记录和性能监控"""
    
    def __init__(self, transport_callable, log_file: str = "logs/mcp_enhanced.jsonl"):
        super().__init__(transport_callable)
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)
        
        # 设置详细日志记录器
        self.logger = logging.getLogger(f"mcp.enhanced.{id(self)}")
        self.logger.setLevel(logging.DEBUG)
        
        # 创建文件处理器
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # 性能统计
        self.call_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_duration": 0.0,
            "tool_usage": {}
        }
    
    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """记录事件到日志文件"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "session_id": str(self._session_id),
            "data": data
        }
        self.logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    def start(self) -> "EnhancedMCPClient":
        """启动客户端并记录启动事件"""
        start_time = time.time()
        self._log_event("client_start", {
            "transport": str(self._transport_callable),
            "start_time": start_time
        })
        
        try:
            result = super().start()
            duration = time.time() - start_time
            self._log_event("client_start_success", {
                "duration_ms": duration * 1000
            })
            return result
        except Exception as e:
            duration = time.time() - start_time
            self._log_event("client_start_failed", {
                "duration_ms": duration * 1000,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise
    
    def stop(self, exc_type=None, exc_val=None, exc_tb=None):
        """停止客户端并记录统计信息"""
        self._log_event("client_stop", {
            "stats": self.call_stats.copy(),
            "exception_info": {
                "type": str(exc_type) if exc_type else None,
                "value": str(exc_val) if exc_val else None
            } if exc_type else None
        })
        super().stop(exc_type, exc_val, exc_tb)
    
    def list_tools_sync(self) -> List:
        """列出工具并记录详细信息"""
        start_time = time.time()
        self._log_event("list_tools_start", {})
        
        try:
            tools = super().list_tools_sync()
            duration = time.time() - start_time
            
            tool_info = []
            for tool in tools:
                tool_spec = tool.tool_spec
                tool_info.append({
                    "name": tool.tool_name,
                    "description": tool_spec.get("description", ""),
                    "input_schema": tool_spec.get("inputSchema", {}),
                    "type": tool.tool_type
                })
            
            self._log_event("list_tools_success", {
                "duration_ms": duration * 1000,
                "tool_count": len(tools),
                "tools": tool_info
            })
            
            return tools
        except Exception as e:
            duration = time.time() - start_time
            self._log_event("list_tools_failed", {
                "duration_ms": duration * 1000,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise
    
    def call_tool_sync(self, tool_use_id: str, name: str, 
                      arguments: dict = None, read_timeout_seconds=None) -> ToolResult:
        """调用工具并记录详细的执行信息"""
        start_time = time.time()
        
        # 记录调用开始
        self._log_event("tool_call_start", {
            "tool_use_id": tool_use_id,
            "tool_name": name,
            "arguments": arguments or {},
            "timeout_seconds": read_timeout_seconds.total_seconds() if read_timeout_seconds else None,
            "start_time": start_time
        })
        
        # 更新统计信息
        self.call_stats["total_calls"] += 1
        if name not in self.call_stats["tool_usage"]:
            self.call_stats["tool_usage"][name] = {
                "count": 0,
                "total_duration": 0.0,
                "success_count": 0,
                "error_count": 0
            }
        
        try:
            result = super().call_tool_sync(tool_use_id, name, arguments, read_timeout_seconds)
            duration = time.time() - start_time
            
            # 更新成功统计
            self.call_stats["successful_calls"] += 1
            self.call_stats["total_duration"] += duration
            self.call_stats["tool_usage"][name]["count"] += 1
            self.call_stats["tool_usage"][name]["total_duration"] += duration
            self.call_stats["tool_usage"][name]["success_count"] += 1
            
            # 分析结果内容
            content_analysis = self._analyze_tool_result(result)
            
            # 记录成功结果
            self._log_event("tool_call_success", {
                "tool_use_id": tool_use_id,
                "tool_name": name,
                "duration_ms": duration * 1000,
                "status": result.status,
                "content_analysis": content_analysis,
                "performance": {
                    "avg_duration_ms": (self.call_stats["tool_usage"][name]["total_duration"] / 
                                      self.call_stats["tool_usage"][name]["count"]) * 1000
                }
            })
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            # 更新失败统计
            self.call_stats["failed_calls"] += 1
            self.call_stats["total_duration"] += duration
            self.call_stats["tool_usage"][name]["count"] += 1
            self.call_stats["tool_usage"][name]["total_duration"] += duration
            self.call_stats["tool_usage"][name]["error_count"] += 1
            
            # 记录失败结果
            self._log_event("tool_call_failed", {
                "tool_use_id": tool_use_id,
                "tool_name": name,
                "duration_ms": duration * 1000,
                "error": str(e),
                "error_type": type(e).__name__,
                "arguments": arguments or {}
            })
            
            raise
    
    def _analyze_tool_result(self, result: ToolResult) -> Dict[str, Any]:
        """分析工具执行结果"""
        analysis = {
            "status": result.status,
            "content_count": len(result.content) if result.content else 0,
            "content_types": [],
            "total_text_length": 0,
            "has_images": False,
            "has_errors": result.status == "error"
        }
        
        if result.content:
            for content in result.content:
                if isinstance(content, dict):
                    if "text" in content:
                        analysis["content_types"].append("text")
                        analysis["total_text_length"] += len(content["text"])
                    elif "image" in content:
                        analysis["content_types"].append("image")
                        analysis["has_images"] = True
                    else:
                        analysis["content_types"].append("unknown")
        
        return analysis
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        report = {
            "session_id": str(self._session_id),
            "timestamp": datetime.now().isoformat(),
            "overall_stats": self.call_stats.copy(),
            "tool_performance": {}
        }
        
        # 计算每个工具的性能指标
        for tool_name, stats in self.call_stats["tool_usage"].items():
            if stats["count"] > 0:
                report["tool_performance"][tool_name] = {
                    "total_calls": stats["count"],
                    "success_rate": stats["success_count"] / stats["count"],
                    "avg_duration_ms": (stats["total_duration"] / stats["count"]) * 1000,
                    "total_duration_ms": stats["total_duration"] * 1000
                }
        
        return report
    
    def export_logs_to_file(self, output_file: str):
        """导出日志到指定文件"""
        report = self.get_performance_report()
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
