"""
增强的Streamlit应用 - 集成测试报告功能
"""

import streamlit as st
import asyncio
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.test_case_manager import TestCaseManager

st.set_page_config(
    page_title="前端自动化测试平台",
    page_icon="🧪",
    layout="wide"
)

# 自定义CSS样式
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .success-metric {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
    .failed-metric {
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
    }
    .report-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧪 前端自动化测试平台 - 增强版")

# 初始化组件
@st.cache_resource
def init_components():
    # 尝试使用真实的 Strands 执行器，如果失败则使用模拟版本
    try:
        from core.strands_test_executor import StrandsTestExecutor
        executor = StrandsTestExecutor()
        print("✅ 使用真实的 Strands 测试执行器")
        return TestCaseManager(), executor
    except Exception as e:
        print(f"⚠️  真实执行器初始化失败，使用模拟版本: {e}")
        from core.mock_strands_executor import MockStrandsTestExecutor
        executor = MockStrandsTestExecutor()
        return TestCaseManager(), executor

test_manager, test_executor = init_components()

# 侧边栏导航
page = st.sidebar.selectbox(
    "选择功能",
    ["📊 仪表板", "📝 测试用例管理", "🚀 执行测试", "📈 测试报告", "📋 历史记录", "⚙️ 系统设置"]
)

# 仪表板页面
if page == "📊 仪表板":
    st.header("📊 测试仪表板")
    
    # 获取最近的测试统计
    try:
        with st.spinner("正在加载测试数据..."):
            history = asyncio.run(test_executor.get_test_history())
            recent_history = history[:50] if history else []  # 最近50次执行
        
        # 调试信息
        st.write(f"🔍 调试信息: 找到 {len(recent_history)} 条历史记录")
        
        if recent_history:
            # 计算统计数据
            total_tests = len(recent_history)
            passed_tests = sum(1 for t in recent_history if t.get('status') == 'passed')
            failed_tests = sum(1 for t in recent_history if t.get('status') == 'failed')
            skipped_tests = sum(1 for t in recent_history if t.get('status') == 'skipped')
            success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
            
            # 显示关键指标
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>{total_tests}</h3>
                    <p>总测试数</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card success-metric">
                    <h3>{passed_tests}</h3>
                    <p>通过</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card failed-metric">
                    <h3>{failed_tests}</h3>
                    <p>失败</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>{skipped_tests}</h3>
                    <p>跳过</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col5:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>{success_rate:.1f}%</h3>
                    <p>成功率</p>
                </div>
                """, unsafe_allow_html=True)
            
            # 趋势图表
            st.subheader("📈 最近测试趋势")
            
            # 准备图表数据
            if recent_history:
                # 确保数据结构正确
                processed_history = []
                for record in recent_history:
                    if isinstance(record, dict):
                        # 确保必要字段存在
                        processed_record = {
                            'test_name': record.get('test_name', '未知测试'),
                            'status': record.get('status', 'unknown'),
                            'start_time': record.get('start_time', datetime.now().isoformat()),
                            'end_time': record.get('end_time', datetime.now().isoformat()),
                            'duration': record.get('duration', 0),
                            'test_id': record.get('test_id', 'unknown')
                        }
                        processed_history.append(processed_record)
                
                if processed_history:
                    df = pd.DataFrame(processed_history)
                    df['date'] = pd.to_datetime(df['start_time']).dt.date
                    daily_stats = df.groupby(['date', 'status']).size().unstack(fill_value=0)
                    
                    # 成功率趋势图
                    if len(daily_stats) > 0:
                        daily_stats['total'] = daily_stats.sum(axis=1)
                        daily_stats['success_rate'] = (daily_stats.get('passed', 0) / daily_stats['total'] * 100)
                        
                        fig = px.line(
                            x=daily_stats.index, 
                            y=daily_stats['success_rate'],
                            title="每日成功率趋势",
                            labels={'x': '日期', 'y': '成功率 (%)'}
                        )
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("暂无足够数据生成趋势图")
                else:
                    st.info("暂无有效的测试历史记录")
            else:
                st.info("暂无测试历史记录")
                
                # 测试状态分布饼图
                status_counts = df['status'].value_counts()
                fig_pie = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    title="测试状态分布"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("暂无测试数据，请先执行一些测试用例。")
            
    except Exception as e:
        st.error(f"加载仪表板数据时出错: {e}")

# 测试用例管理页面
elif page == "📝 测试用例管理":
    st.header("📝 测试用例管理")
    
    tab1, tab2 = st.tabs(["创建测试用例", "查看测试用例"])
    
    with tab1:
        with st.form("create_test_case"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("测试用例名称*")
                url = st.text_input("测试URL*")
                tags_input = st.text_input("标签 (用逗号分隔)", placeholder="例如: 登录,功能测试,回归测试")
            
            with col2:
                description = st.text_area("测试描述", height=100)
                expected_result = st.text_area("预期结果*", height=100)
            
            st.subheader("测试步骤")
            steps = []
            for i in range(8):  # 最多8个步骤
                step = st.text_input(f"步骤 {i+1}", key=f"step_{i}")
                if step:
                    steps.append(step)
            
            if st.form_submit_button("创建测试用例", type="primary"):
                if name and url and expected_result and steps:
                    # 处理标签
                    tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()] if tags_input else []
                    
                    # 添加导航步骤
                    full_steps = [f"导航到 {url}"] + steps
                    
                    # 将预期结果转换为列表格式
                    expected_results_list = [expected_result] if expected_result else []
                    
                    test_case = asyncio.run(
                        test_manager.create_test_case(
                            name=name, 
                            description=description, 
                            steps=full_steps, 
                            expected_results=expected_results_list,
                            tags=tags
                        )
                    )
                    
                    st.success(f"✅ 测试用例创建成功！ID: {test_case['id']}")
                    st.rerun()
                else:
                    st.error("❌ 请填写所有必填字段")
    
    with tab2:
        st.subheader("现有测试用例")
        test_cases = asyncio.run(test_manager.list_test_cases())
        
        if test_cases:
            # 搜索和过滤
            col1, col2 = st.columns(2)
            with col1:
                search_term = st.text_input("🔍 搜索测试用例", placeholder="输入名称或描述关键词")
            with col2:
                all_tags = set()
                for case in test_cases:
                    all_tags.update(case.get('tags', []))
                selected_tags = st.multiselect("🏷️ 按标签过滤", list(all_tags))
            
            # 过滤测试用例
            filtered_cases = test_cases
            if search_term:
                filtered_cases = [
                    case for case in filtered_cases
                    if search_term.lower() in case['name'].lower() or 
                       search_term.lower() in case.get('description', '').lower()
                ]
            if selected_tags:
                filtered_cases = [
                    case for case in filtered_cases
                    if any(tag in case.get('tags', []) for tag in selected_tags)
                ]
            
            st.write(f"显示 {len(filtered_cases)} / {len(test_cases)} 个测试用例")
            
            for case in filtered_cases:
                with st.expander(f"🧪 {case['name']} (ID: {case['id'][:8]}...)"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**📝 描述**: {case.get('description', '无')}")
                        st.write(f"**🕒 创建时间**: {case['created_at']}")
                        
                        if case.get('tags'):
                            tags_html = " ".join([f"<span style='background:#007bff;color:white;padding:2px 8px;border-radius:12px;font-size:0.8em;margin-right:5px;'>{tag}</span>" for tag in case['tags']])
                            st.markdown(f"**🏷️ 标签**: {tags_html}", unsafe_allow_html=True)
                        
                        st.write("**📋 测试步骤**:")
                        for i, step in enumerate(case['steps'], 1):
                            st.write(f"   {i}. {step}")
                        
                        # 处理预期结果（可能是列表或字符串）
                        expected_results = case.get('expected_results', [])
                        if expected_results:
                            if isinstance(expected_results, list):
                                st.write("**✅ 预期结果**:")
                                for i, result in enumerate(expected_results, 1):
                                    st.write(f"   {i}. {result}")
                            else:
                                st.write(f"**✅ 预期结果**: {expected_results}")
                        else:
                            st.write("**✅ 预期结果**: 暂无")
                    
                    with col2:
                        if st.button(f"🚀 执行测试", key=f"run_{case['id']}"):
                            st.session_state.selected_test = case
                            st.session_state.page = "🚀 执行测试"
                            st.rerun()
        else:
            st.info("📭 暂无测试用例，请先创建一些测试用例。")

# 执行测试页面
elif page == "🚀 执行测试":
    st.header("🚀 执行测试")
    
    test_cases = asyncio.run(test_manager.list_test_cases())
    
    if test_cases:
        # 检查是否有预选的测试用例
        if 'selected_test' in st.session_state:
            selected_case = st.session_state.selected_test
            st.info(f"已选择测试用例: {selected_case['name']}")
        else:
            selected_case = st.selectbox(
                "选择要执行的测试用例",
                test_cases,
                format_func=lambda x: f"🧪 {x['name']} (ID: {x['id'][:8]}...)"
            )
        
        # 显示测试用例详情
        with st.expander("📋 测试用例详情", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**名称**: {selected_case['name']}")
                st.write(f"**描述**: {selected_case.get('description', '无')}")
                if selected_case.get('tags'):
                    st.write(f"**标签**: {', '.join(selected_case['tags'])}")
            with col2:
                st.write(f"**步骤数**: {len(selected_case['steps'])}")
                st.write(f"**创建时间**: {selected_case['created_at']}")
        
        # 执行选项
        col1, col2 = st.columns(2)
        with col1:
            generate_reports = st.checkbox("生成详细报告", value=True)
        with col2:
            save_screenshots = st.checkbox("保存截图", value=True)
        
        if st.button("🚀 开始执行测试", type="primary", use_container_width=True):
            with st.spinner("🔄 正在执行测试，请稍候..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    status_text.text("正在初始化测试环境...")
                    progress_bar.progress(20)
                    
                    status_text.text("正在执行测试步骤...")
                    progress_bar.progress(60)
                    
                    result = asyncio.run(test_executor.execute_test_case(selected_case))
                    
                    progress_bar.progress(100)
                    status_text.text("测试执行完成！")
                    
                    # 显示执行结果
                    test_result = result['test_result']
                    execution_summary = result['execution_summary']
                    
                    # 结果状态
                    if test_result.status == 'passed':
                        st.success("✅ 测试执行成功！")
                    elif test_result.status == 'failed':
                        st.error("❌ 测试执行失败！")
                    else:
                        st.warning("⚠️ 测试被跳过")
                    
                    # 执行摘要
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("执行状态", test_result.status.upper())
                    with col2:
                        st.metric("执行时间", f"{test_result.duration:.2f}s")
                    with col3:
                        st.metric("总步骤", len(test_result.steps))
                    with col4:
                        passed_steps = sum(1 for s in test_result.steps if s.status == 'passed')
                        st.metric("通过步骤", f"{passed_steps}/{len(test_result.steps)}")
                    
                    # 步骤详情
                    st.subheader("📋 步骤执行详情")
                    for i, step in enumerate(test_result.steps, 1):
                        status_icon = "✅" if step.status == 'passed' else "❌" if step.status == 'failed' else "⚠️"
                        
                        with st.expander(f"{status_icon} 步骤 {i}: {step.name}"):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"**描述**: {step.description}")
                                if step.error_message:
                                    st.error(f"**错误**: {step.error_message}")
                            with col2:
                                st.write(f"**状态**: {step.status}")
                                st.write(f"**耗时**: {step.duration:.2f}s")
                            
                            if step.screenshot:
                                st.image(f"data:image/png;base64,{step.screenshot}", caption=f"步骤 {i} 截图")
                    
                    # 报告文件
                    if generate_reports and 'report_files' in result:
                        st.subheader("📊 生成的报告")
                        report_files = result['report_files']
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if 'html' in report_files:
                                st.success(f"📄 HTML报告已生成")
                                if st.button("查看HTML报告"):
                                    # 在新标签页打开HTML报告
                                    st.markdown(f"[点击查看HTML报告]({report_files['html']})")
                        
                        with col2:
                            if 'json' in report_files:
                                st.success(f"📋 JSON报告已生成")
                                with open(report_files['json'], 'r', encoding='utf-8') as f:
                                    json_data = json.load(f)
                                if st.button("下载JSON报告"):
                                    st.download_button(
                                        label="下载JSON",
                                        data=json.dumps(json_data, ensure_ascii=False, indent=2),
                                        file_name=f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                        mime="application/json"
                                    )
                        
                        with col3:
                            if 'allure' in report_files:
                                st.success(f"📈 Allure报告已生成")
                                st.info(f"Allure报告目录: {report_files['allure']}")
                    
                    # 原始输出
                    with st.expander("🔍 原始执行输出"):
                        st.text_area("详细输出", result['raw_output'], height=300)
                    
                except Exception as e:
                    st.error(f"❌ 测试执行失败: {str(e)}")
                    st.exception(e)
                finally:
                    # 清除进度条
                    progress_bar.empty()
                    status_text.empty()
    else:
        st.info("📭 请先创建测试用例")

# 测试报告页面
elif page == "📈 测试报告":
    st.header("📈 测试报告")
    
    # 获取报告文件列表
    reports_dir = Path("./reports")
    if not reports_dir.exists():
        st.warning("报告目录不存在，请先执行测试")
    else:
        # HTML 报告
        html_reports = list((reports_dir / "html").glob("*.html")) if (reports_dir / "html").exists() else []
        json_reports = list((reports_dir / "json").glob("*.json")) if (reports_dir / "json").exists() else []
        
        if not html_reports and not json_reports:
            st.info("暂无测试报告，请先执行测试")
        else:
            # 报告类型选择
            report_type = st.selectbox("选择报告类型", ["HTML报告", "JSON报告"])
            
            if report_type == "HTML报告" and html_reports:
                st.subheader("📄 HTML 测试报告")
                
                # 选择报告文件
                selected_html = st.selectbox(
                    "选择报告文件",
                    html_reports,
                    format_func=lambda x: f"{x.name} ({x.stat().st_mtime})"
                )
                
                if selected_html:
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("📖 在新窗口打开"):
                            st.markdown(f"[点击打开报告]({selected_html.absolute()})")
                    
                    with col2:
                        # 读取并显示HTML内容
                        try:
                            with open(selected_html, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                            st.components.v1.html(html_content, height=600, scrolling=True)
                        except Exception as e:
                            st.error(f"读取HTML报告失败: {e}")
            
            elif report_type == "JSON报告" and json_reports:
                st.subheader("📋 JSON 测试报告")
                
                # 选择报告文件
                selected_json = st.selectbox(
                    "选择报告文件",
                    json_reports,
                    format_func=lambda x: f"{x.name} ({datetime.fromtimestamp(x.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')})"
                )
                
                if selected_json:
                    try:
                        with open(selected_json, 'r', encoding='utf-8') as f:
                            report_data = json.load(f)
                        
                        # 显示报告摘要
                        if isinstance(report_data, dict) and 'summary' in report_data:
                            summary = report_data['summary']
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("总测试数", summary.get('total_tests', 0))
                            with col2:
                                st.metric("通过", summary.get('passed_tests', 0))
                            with col3:
                                st.metric("失败", summary.get('failed_tests', 0))
                            with col4:
                                st.metric("成功率", f"{summary.get('success_rate', 0):.1f}%")
                        
                        # 显示详细数据
                        st.subheader("📊 详细数据")
                        st.json(report_data)
                        
                        # 下载按钮
                        st.download_button(
                            label="📥 下载JSON报告",
                            data=json.dumps(report_data, ensure_ascii=False, indent=2),
                            file_name=selected_json.name,
                            mime="application/json"
                        )
                        
                    except Exception as e:
                        st.error(f"读取JSON报告失败: {e}")
                        st.exception(e)

# 历史记录页面
elif page == "📋 历史记录":
    st.header("📋 测试历史记录")
    
    try:
        # 获取测试历史
        history = asyncio.run(test_executor.get_test_history())
        
        if not history:
            st.info("暂无测试历史记录")
        else:
            # 过滤和搜索
            col1, col2 = st.columns([2, 1])
            with col1:
                search_term = st.text_input("🔍 搜索测试用例", placeholder="输入测试名称或ID")
            with col2:
                status_filter = st.selectbox("状态筛选", ["全部", "passed", "failed", "skipped"])
            
            # 应用过滤
            filtered_history = history
            if search_term:
                filtered_history = [
                    record for record in filtered_history 
                    if search_term.lower() in record.get('test_name', '').lower() 
                    or search_term.lower() in record.get('test_id', '').lower()
                ]
            
            if status_filter != "全部":
                filtered_history = [
                    record for record in filtered_history 
                    if record.get('status') == status_filter
                ]
            
            # 显示统计信息
            if filtered_history:
                st.subheader("📊 统计概览")
                
                # 处理数据确保字段存在
                processed_history = []
                for record in filtered_history:
                    processed_record = {
                        'test_name': record.get('test_name', '未知测试'),
                        'status': record.get('status', 'unknown'),
                        'start_time': record.get('start_time', datetime.now().isoformat()),
                        'duration': record.get('duration', 0),
                        'test_id': record.get('test_id', 'unknown')
                    }
                    processed_history.append(processed_record)
                
                # 状态统计
                status_counts = {}
                for record in processed_history:
                    status = record['status']
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("总计", len(processed_history))
                with col2:
                    st.metric("通过", status_counts.get('passed', 0))
                with col3:
                    st.metric("失败", status_counts.get('failed', 0))
                with col4:
                    success_rate = (status_counts.get('passed', 0) / len(processed_history)) * 100 if processed_history else 0
                    st.metric("成功率", f"{success_rate:.1f}%")
                
                # 历史记录表格
                st.subheader("📋 详细记录")
                
                # 转换为DataFrame
                df = pd.DataFrame(processed_history)
                df['start_time'] = pd.to_datetime(df['start_time'])
                df = df.sort_values('start_time', ascending=False)
                
                # 格式化显示
                display_df = df.copy()
                display_df['开始时间'] = display_df['start_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                display_df['测试名称'] = display_df['test_name']
                display_df['状态'] = display_df['status'].apply(
                    lambda x: "✅ 通过" if x == 'passed' else "❌ 失败" if x == 'failed' else "⏭️ 跳过" if x == 'skipped' else "❓ 未知"
                )
                display_df['执行时长'] = display_df['duration'].apply(lambda x: f"{x:.2f}s")
                display_df['测试ID'] = display_df['test_id']
                
                # 显示表格
                st.dataframe(
                    display_df[['开始时间', '测试名称', '状态', '执行时长', '测试ID']],
                    use_container_width=True,
                    hide_index=True
                )
                
                # 趋势图
                if len(df) > 1:
                    st.subheader("📈 执行趋势")
                    
                    # 按日期分组
                    df['date'] = df['start_time'].dt.date
                    daily_stats = df.groupby(['date', 'status']).size().unstack(fill_value=0)
                    
                    if not daily_stats.empty:
                        # 成功率趋势
                        daily_stats['total'] = daily_stats.sum(axis=1)
                        daily_stats['success_rate'] = (daily_stats.get('passed', 0) / daily_stats['total'] * 100)
                        
                        fig = px.line(
                            x=daily_stats.index,
                            y=daily_stats['success_rate'],
                            title="每日成功率趋势",
                            labels={'x': '日期', 'y': '成功率 (%)'}
                        )
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # 执行次数趋势
                        fig2 = px.bar(
                            x=daily_stats.index,
                            y=daily_stats['total'],
                            title="每日测试执行次数",
                            labels={'x': '日期', 'y': '执行次数'}
                        )
                        fig2.update_layout(height=400)
                        st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("没有符合条件的测试记录")
                
    except Exception as e:
        st.error(f"加载历史记录失败: {e}")
        st.exception(e)

# 系统设置页面
elif page == "⚙️ 系统设置":
    st.header("⚙️ 系统设置")
    
    st.subheader("🔧 执行器配置")
    
    # AWS 区域设置
    current_region = st.session_state.get('aws_region', 'us-west-2')
    new_region = st.selectbox(
        "AWS 区域",
        ['us-west-2', 'us-east-1', 'eu-west-1', 'ap-southeast-1'],
        index=['us-west-2', 'us-east-1', 'eu-west-1', 'ap-southeast-1'].index(current_region)
    )
    
    if new_region != current_region:
        st.session_state.aws_region = new_region
        st.success(f"AWS 区域已更新为: {new_region}")
        st.info("请重新启动应用以应用更改")
    
    # 执行器类型选择
    executor_type = st.selectbox(
        "执行器类型",
        ["Strands + MCP Playwright", "Mock 执行器"],
        index=0 if isinstance(test_executor, type(test_executor)) else 1
    )
    
    st.subheader("📊 系统状态")
    
    # 显示当前配置
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**执行器类型**: {type(test_executor).__name__}")
        st.info(f"**AWS 区域**: {getattr(test_executor, 'region', '未知')}")
        st.info(f"**模型**: {getattr(test_executor, 'model_id', '未知')}")
    
    with col2:
        # 检查目录状态
        reports_dir = Path("./reports")
        test_cases_file = Path("./test_cases/test_cases.json")
        
        st.info(f"**报告目录**: {'✅ 存在' if reports_dir.exists() else '❌ 不存在'}")
        st.info(f"**测试用例文件**: {'✅ 存在' if test_cases_file.exists() else '❌ 不存在'}")
        
        # 统计信息
        if reports_dir.exists():
            html_count = len(list((reports_dir / "html").glob("*.html"))) if (reports_dir / "html").exists() else 0
            json_count = len(list((reports_dir / "json").glob("*.json"))) if (reports_dir / "json").exists() else 0
            st.info(f"**报告文件**: HTML({html_count}) JSON({json_count})")
    
    # 清理功能
    st.subheader("🧹 系统清理")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 清理报告文件"):
            try:
                if reports_dir.exists():
                    import shutil
                    shutil.rmtree(reports_dir)
                    reports_dir.mkdir(parents=True, exist_ok=True)
                    (reports_dir / "html").mkdir(exist_ok=True)
                    (reports_dir / "json").mkdir(exist_ok=True)
                    st.success("报告文件已清理")
                else:
                    st.info("报告目录不存在")
            except Exception as e:
                st.error(f"清理失败: {e}")
    
    with col2:
        if st.button("🔄 重置测试用例"):
            if st.session_state.get('confirm_reset'):
                try:
                    test_manager.test_cases = []
                    test_manager.save_test_cases()
                    st.success("测试用例已重置")
                    st.session_state.confirm_reset = False
                except Exception as e:
                    st.error(f"重置失败: {e}")
            else:
                st.session_state.confirm_reset = True
                st.warning("再次点击确认重置")

# 清除选中的测试用例
if 'selected_test' in st.session_state and page != "🚀 执行测试":
    del st.session_state.selected_test
