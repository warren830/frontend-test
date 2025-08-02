"""
MCP 日志分析工具 - 分析和可视化 MCP 调用日志
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter


class MCPLogAnalyzer:
    """MCP 日志分析器"""
    
    def __init__(self, log_file: str):
        self.log_file = Path(log_file)
        self.logs = []
        self.df = None
        self.load_logs()
    
    def load_logs(self):
        """加载日志文件"""
        if not self.log_file.exists():
            print(f"日志文件不存在: {self.log_file}")
            return
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    log_entry = json.loads(line.strip())
                    self.logs.append(log_entry)
                except json.JSONDecodeError:
                    continue
        
        if self.logs:
            self.df = pd.DataFrame(self.logs)
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        
        print(f"加载了 {len(self.logs)} 条日志记录")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """获取会话摘要"""
        if not self.logs:
            return {}
        
        sessions = defaultdict(lambda: {
            'start_time': None,
            'end_time': None,
            'tool_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'tools_used': set(),
            'total_duration': 0.0
        })
        
        for log in self.logs:
            session_id = log.get('session_id', 'unknown')
            event_type = log.get('event_type', '')
            timestamp = datetime.fromisoformat(log['timestamp'])
            
            session = sessions[session_id]
            
            if session['start_time'] is None or timestamp < session['start_time']:
                session['start_time'] = timestamp
            if session['end_time'] is None or timestamp > session['end_time']:
                session['end_time'] = timestamp
            
            if event_type == 'tool_call_start':
                session['tool_calls'] += 1
                session['tools_used'].add(log['data'].get('tool_name', ''))
            elif event_type == 'tool_call_success':
                session['successful_calls'] += 1
                session['total_duration'] += log['data'].get('duration_ms', 0) / 1000
            elif event_type == 'tool_call_failed':
                session['failed_calls'] += 1
                session['total_duration'] += log['data'].get('duration_ms', 0) / 1000
        
        # 转换 set 为 list 以便 JSON 序列化
        for session in sessions.values():
            session['tools_used'] = list(session['tools_used'])
            if session['start_time']:
                session['start_time'] = session['start_time'].isoformat()
            if session['end_time']:
                session['end_time'] = session['end_time'].isoformat()
        
        return dict(sessions)
    
    def get_tool_performance_stats(self) -> Dict[str, Any]:
        """获取工具性能统计"""
        tool_stats = defaultdict(lambda: {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_duration_ms': 0,
            'min_duration_ms': float('inf'),
            'max_duration_ms': 0,
            'durations': []
        })
        
        for log in self.logs:
            event_type = log.get('event_type', '')
            if event_type in ['tool_call_success', 'tool_call_failed']:
                tool_name = log['data'].get('tool_name', 'unknown')
                duration_ms = log['data'].get('duration_ms', 0)
                
                stats = tool_stats[tool_name]
                stats['total_calls'] += 1
                stats['total_duration_ms'] += duration_ms
                stats['durations'].append(duration_ms)
                
                if duration_ms < stats['min_duration_ms']:
                    stats['min_duration_ms'] = duration_ms
                if duration_ms > stats['max_duration_ms']:
                    stats['max_duration_ms'] = duration_ms
                
                if event_type == 'tool_call_success':
                    stats['successful_calls'] += 1
                else:
                    stats['failed_calls'] += 1
        
        # 计算平均值和成功率
        for tool_name, stats in tool_stats.items():
            if stats['total_calls'] > 0:
                stats['avg_duration_ms'] = stats['total_duration_ms'] / stats['total_calls']
                stats['success_rate'] = stats['successful_calls'] / stats['total_calls']
                
                # 计算中位数
                if stats['durations']:
                    stats['median_duration_ms'] = sorted(stats['durations'])[len(stats['durations']) // 2]
            
            # 清理无限值
            if stats['min_duration_ms'] == float('inf'):
                stats['min_duration_ms'] = 0
        
        return dict(tool_stats)
    
    def get_error_analysis(self) -> Dict[str, Any]:
        """获取错误分析"""
        errors = []
        error_types = Counter()
        error_by_tool = defaultdict(list)
        
        for log in self.logs:
            if log.get('event_type') == 'tool_call_failed':
                error_info = {
                    'timestamp': log['timestamp'],
                    'tool_name': log['data'].get('tool_name', 'unknown'),
                    'error': log['data'].get('error', ''),
                    'error_type': log['data'].get('error_type', 'unknown'),
                    'duration_ms': log['data'].get('duration_ms', 0)
                }
                errors.append(error_info)
                error_types[error_info['error_type']] += 1
                error_by_tool[error_info['tool_name']].append(error_info)
        
        return {
            'total_errors': len(errors),
            'error_types': dict(error_types),
            'error_by_tool': dict(error_by_tool),
            'recent_errors': errors[-10:] if errors else []
        }
    
    def generate_performance_report(self, output_file: str = None) -> str:
        """生成性能报告"""
        report = []
        report.append("# MCP 性能分析报告")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"日志文件: {self.log_file}")
        report.append(f"总日志条数: {len(self.logs)}")
        report.append("")
        
        # 会话摘要
        sessions = self.get_session_summary()
        report.append("## 会话摘要")
        for session_id, session in sessions.items():
            report.append(f"### 会话 {session_id[:8]}...")
            report.append(f"- 开始时间: {session['start_time']}")
            report.append(f"- 结束时间: {session['end_time']}")
            report.append(f"- 工具调用总数: {session['tool_calls']}")
            report.append(f"- 成功调用: {session['successful_calls']}")
            report.append(f"- 失败调用: {session['failed_calls']}")
            report.append(f"- 使用的工具: {', '.join(session['tools_used'])}")
            report.append(f"- 总执行时间: {session['total_duration']:.2f}秒")
            report.append("")
        
        # 工具性能统计
        tool_stats = self.get_tool_performance_stats()
        report.append("## 工具性能统计")
        for tool_name, stats in tool_stats.items():
            report.append(f"### {tool_name}")
            report.append(f"- 总调用次数: {stats['total_calls']}")
            report.append(f"- 成功率: {stats['success_rate']:.2%}")
            report.append(f"- 平均执行时间: {stats['avg_duration_ms']:.2f}ms")
            report.append(f"- 中位数执行时间: {stats['median_duration_ms']:.2f}ms")
            report.append(f"- 最短执行时间: {stats['min_duration_ms']:.2f}ms")
            report.append(f"- 最长执行时间: {stats['max_duration_ms']:.2f}ms")
            report.append("")
        
        # 错误分析
        error_analysis = self.get_error_analysis()
        report.append("## 错误分析")
        report.append(f"总错误数: {error_analysis['total_errors']}")
        report.append("### 错误类型分布")
        for error_type, count in error_analysis['error_types'].items():
            report.append(f"- {error_type}: {count}")
        report.append("")
        
        report.append("### 各工具错误情况")
        for tool_name, errors in error_analysis['error_by_tool'].items():
            report.append(f"- {tool_name}: {len(errors)} 个错误")
        report.append("")
        
        if error_analysis['recent_errors']:
            report.append("### 最近的错误")
            for error in error_analysis['recent_errors']:
                report.append(f"- {error['timestamp']}: {error['tool_name']} - {error['error']}")
        
        report_text = "\n".join(report)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"报告已保存到: {output_file}")
        
        return report_text
    
    def plot_tool_performance(self, save_path: str = None):
        """绘制工具性能图表"""
        tool_stats = self.get_tool_performance_stats()
        
        if not tool_stats:
            print("没有工具性能数据可绘制")
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # 工具调用次数
        tools = list(tool_stats.keys())
        call_counts = [stats['total_calls'] for stats in tool_stats.values()]
        
        ax1.bar(tools, call_counts)
        ax1.set_title('工具调用次数')
        ax1.set_xlabel('工具名称')
        ax1.set_ylabel('调用次数')
        ax1.tick_params(axis='x', rotation=45)
        
        # 工具成功率
        success_rates = [stats['success_rate'] * 100 for stats in tool_stats.values()]
        
        ax2.bar(tools, success_rates)
        ax2.set_title('工具成功率')
        ax2.set_xlabel('工具名称')
        ax2.set_ylabel('成功率 (%)')
        ax2.tick_params(axis='x', rotation=45)
        
        # 平均执行时间
        avg_durations = [stats['avg_duration_ms'] for stats in tool_stats.values()]
        
        ax3.bar(tools, avg_durations)
        ax3.set_title('平均执行时间')
        ax3.set_xlabel('工具名称')
        ax3.set_ylabel('时间 (ms)')
        ax3.tick_params(axis='x', rotation=45)
        
        # 执行时间分布（箱线图）
        duration_data = []
        tool_labels = []
        for tool_name, stats in tool_stats.items():
            if stats['durations']:
                duration_data.append(stats['durations'])
                tool_labels.append(tool_name)
        
        if duration_data:
            ax4.boxplot(duration_data, labels=tool_labels)
            ax4.set_title('执行时间分布')
            ax4.set_xlabel('工具名称')
            ax4.set_ylabel('时间 (ms)')
            ax4.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {save_path}")
        
        plt.show()


def main():
    """主函数 - 演示如何使用日志分析器"""
    analyzer = MCPLogAnalyzer("logs/mcp_enhanced.jsonl")
    
    # 生成报告
    report = analyzer.generate_performance_report("reports/mcp_performance_report.md")
    print("性能报告:")
    print(report[:1000] + "..." if len(report) > 1000 else report)
    
    # 绘制图表
    analyzer.plot_tool_performance("reports/mcp_performance_charts.png")


if __name__ == "__main__":
    main()
