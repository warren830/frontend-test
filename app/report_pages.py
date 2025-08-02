"""
测试报告相关页面
"""

import streamlit as st
import asyncio
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, timedelta
import base64

def render_test_reports_page(test_executor):
    """渲染测试报告页面"""
    st.header("📈 测试报告")
    
    # 报告类型选择
    report_type = st.selectbox(
        "选择报告类型",
        ["📊 汇总报告", "📋 详细报告", "📈 趋势分析", "🔍 Allure报告"]
    )
    
    if report_type == "📊 汇总报告":
        render_summary_report(test_executor)
    elif report_type == "📋 详细报告":
        render_detailed_report(test_executor)
    elif report_type == "📈 趋势分析":
        render_trend_analysis(test_executor)
    elif report_type == "🔍 Allure报告":
        render_allure_report()

def render_summary_report(test_executor):
    """渲染汇总报告"""
    st.subheader("📊 测试执行汇总")
    
    try:
        # 获取测试历史
        history = asyncio.run(test_executor.get_test_history())
        
        if not history:
            st.info("暂无测试数据")
            return
        
        # 时间范围选择
        col1, col2 = st.columns(2)
        with col1:
            days_range = st.selectbox("选择时间范围", [7, 14, 30, 60, 90], index=2)
        with col2:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_range)
            st.write(f"📅 {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        
        # 过滤数据
        filtered_history = [
            result for result in history
            if start_date <= datetime.fromisoformat(result.get('start_time', '')) <= end_date
        ]
        
        if not filtered_history:
            st.warning(f"在选定的 {days_range} 天内没有测试数据")
            return
        
        # 计算统计数据
        total_tests = len(filtered_history)
        passed_tests = sum(1 for t in filtered_history if t.get('status') == 'passed')
        failed_tests = sum(1 for t in filtered_history if t.get('status') == 'failed')
        skipped_tests = sum(1 for t in filtered_history if t.get('status') == 'skipped')
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # 显示关键指标
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("总测试数", total_tests)
        with col2:
            st.metric("通过", passed_tests, delta=f"{(passed_tests/total_tests*100):.1f}%")
        with col3:
            st.metric("失败", failed_tests, delta=f"{(failed_tests/total_tests*100):.1f}%")
        with col4:
            st.metric("跳过", skipped_tests, delta=f"{(skipped_tests/total_tests*100):.1f}%")
        with col5:
            st.metric("成功率", f"{success_rate:.1f}%")
        
        # 测试状态分布图
        col1, col2 = st.columns(2)
        
        with col1:
            # 饼图
            status_counts = pd.Series([passed_tests, failed_tests, skipped_tests], 
                                    index=['通过', '失败', '跳过'])
            fig_pie = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="测试状态分布",
                color_discrete_map={'通过': '#28a745', '失败': '#dc3545', '跳过': '#ffc107'}
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # 柱状图
            fig_bar = px.bar(
                x=status_counts.index,
                y=status_counts.values,
                title="测试状态统计",
                color=status_counts.index,
                color_discrete_map={'通过': '#28a745', '失败': '#dc3545', '跳过': '#ffc107'}
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # 按测试用例分组统计
        st.subheader("📋 按测试用例统计")
        
        df = pd.DataFrame(filtered_history)
        if not df.empty:
            test_stats = df.groupby('test_name').agg({
                'status': ['count', lambda x: (x == 'passed').sum(), lambda x: (x == 'failed').sum()],
                'duration': 'mean'
            }).round(2)
            
            test_stats.columns = ['总执行次数', '通过次数', '失败次数', '平均耗时(s)']
            test_stats['成功率(%)'] = (test_stats['通过次数'] / test_stats['总执行次数'] * 100).round(1)
            
            st.dataframe(test_stats, use_container_width=True)
        
        # 执行时间分析
        st.subheader("⏱️ 执行时间分析")
        
        durations = [float(t.get('duration', 0)) for t in filtered_history]
        if durations:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("平均执行时间", f"{sum(durations)/len(durations):.2f}s")
            with col2:
                st.metric("最短执行时间", f"{min(durations):.2f}s")
            with col3:
                st.metric("最长执行时间", f"{max(durations):.2f}s")
            
            # 执行时间分布直方图
            fig_hist = px.histogram(
                x=durations,
                title="执行时间分布",
                labels={'x': '执行时间(秒)', 'y': '频次'},
                nbins=20
            )
            st.plotly_chart(fig_hist, use_container_width=True)
        
    except Exception as e:
        st.error(f"生成汇总报告时出错: {e}")

def render_detailed_report(test_executor):
    """渲染详细报告"""
    st.subheader("📋 详细测试报告")
    
    try:
        # 获取所有报告文件
        reports_dir = Path("./reports")
        
        # HTML报告
        html_reports = list((reports_dir / "html").glob("*.html")) if (reports_dir / "html").exists() else []
        json_reports = list((reports_dir / "json").glob("*.json")) if (reports_dir / "json").exists() else []
        
        if not html_reports and not json_reports:
            st.info("暂无详细报告，请先执行一些测试用例")
            return
        
        # 报告列表
        st.subheader("📄 可用报告")
        
        # HTML报告
        if html_reports:
            st.write("**HTML报告:**")
            for html_file in sorted(html_reports, reverse=True)[:10]:  # 显示最近10个
                file_time = datetime.fromtimestamp(html_file.stat().st_mtime)
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.write(f"📄 {html_file.name}")
                with col2:
                    st.write(f"🕒 {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
                with col3:
                    # 读取HTML文件并提供下载
                    with open(html_file, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    st.download_button(
                        label="下载",
                        data=html_content,
                        file_name=html_file.name,
                        mime="text/html",
                        key=f"download_html_{html_file.name}"
                    )
        
        # JSON报告
        if json_reports:
            st.write("**JSON报告:**")
            selected_json = st.selectbox(
                "选择JSON报告查看详情",
                json_reports,
                format_func=lambda x: f"{x.name} ({datetime.fromtimestamp(x.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')})"
            )
            
            if selected_json:
                with open(selected_json, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                
                # 显示报告信息
                report_info = report_data.get('report_info', {})
                st.write("**报告信息:**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("总测试数", report_info.get('total_tests', 0))
                with col2:
                    st.metric("通过", report_info.get('passed', 0))
                with col3:
                    st.metric("失败", report_info.get('failed', 0))
                
                # 显示测试结果
                test_results = report_data.get('test_results', [])
                if test_results:
                    st.write("**测试结果详情:**")
                    for i, result in enumerate(test_results):
                        status_icon = "✅" if result.get('status') == 'passed' else "❌" if result.get('status') == 'failed' else "⚠️"
                        
                        with st.expander(f"{status_icon} {result.get('test_name', f'测试 {i+1}')}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**状态**: {result.get('status', 'unknown')}")
                                st.write(f"**开始时间**: {result.get('start_time', 'N/A')}")
                                st.write(f"**结束时间**: {result.get('end_time', 'N/A')}")
                            with col2:
                                st.write(f"**执行时间**: {result.get('duration', 0):.2f}s")
                                st.write(f"**测试ID**: {result.get('test_id', 'N/A')}")
                            
                            if result.get('error_message'):
                                st.error(f"**错误信息**: {result['error_message']}")
                            
                            # 显示步骤
                            steps = result.get('steps', [])
                            if steps:
                                st.write("**执行步骤:**")
                                for j, step in enumerate(steps):
                                    step_status = "✅" if step.get('status') == 'passed' else "❌" if step.get('status') == 'failed' else "⚠️"
                                    st.write(f"  {step_status} {j+1}. {step.get('name', 'Unknown Step')} ({step.get('duration', 0):.2f}s)")
                
                # 提供下载
                st.download_button(
                    label="下载完整JSON报告",
                    data=json.dumps(report_data, ensure_ascii=False, indent=2),
                    file_name=selected_json.name,
                    mime="application/json"
                )
        
    except Exception as e:
        st.error(f"加载详细报告时出错: {e}")

def render_trend_analysis(test_executor):
    """渲染趋势分析"""
    st.subheader("📈 测试趋势分析")
    
    try:
        # 时间范围选择
        days_range = st.selectbox("选择分析时间范围", [7, 14, 30, 60, 90], index=2)
        
        # 获取趋势数据
        trend_data = asyncio.run(test_executor.generate_trend_report(days_range))
        
        if not trend_data.get('daily_trend'):
            st.info(f"在过去 {days_range} 天内没有足够的数据进行趋势分析")
            return
        
        # 显示总体统计
        overall_stats = trend_data.get('overall_stats', {})
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总执行次数", overall_stats.get('total', 0))
        with col2:
            st.metric("通过", overall_stats.get('passed', 0))
        with col3:
            st.metric("失败", overall_stats.get('failed', 0))
        with col4:
            success_rate = (overall_stats.get('passed', 0) / overall_stats.get('total', 1) * 100)
            st.metric("整体成功率", f"{success_rate:.1f}%")
        
        # 趋势图表
        daily_trend = trend_data.get('daily_trend', [])
        df_trend = pd.DataFrame(daily_trend)
        
        if not df_trend.empty:
            # 成功率趋势线
            fig_success = px.line(
                df_trend,
                x='date',
                y='success_rate',
                title='每日成功率趋势',
                labels={'date': '日期', 'success_rate': '成功率 (%)'},
                markers=True
            )
            fig_success.update_layout(height=400)
            st.plotly_chart(fig_success, use_container_width=True)
            
            # 每日测试数量趋势
            fig_volume = go.Figure()
            fig_volume.add_trace(go.Scatter(
                x=df_trend['date'],
                y=df_trend['passed'],
                mode='lines+markers',
                name='通过',
                line=dict(color='green')
            ))
            fig_volume.add_trace(go.Scatter(
                x=df_trend['date'],
                y=df_trend['failed'],
                mode='lines+markers',
                name='失败',
                line=dict(color='red')
            ))
            fig_volume.add_trace(go.Scatter(
                x=df_trend['date'],
                y=df_trend['total'],
                mode='lines+markers',
                name='总数',
                line=dict(color='blue')
            ))
            
            fig_volume.update_layout(
                title='每日测试数量趋势',
                xaxis_title='日期',
                yaxis_title='测试数量',
                height=400
            )
            st.plotly_chart(fig_volume, use_container_width=True)
            
            # 堆叠面积图
            fig_stack = px.area(
                df_trend,
                x='date',
                y=['passed', 'failed', 'skipped'],
                title='每日测试状态分布',
                labels={'date': '日期', 'value': '测试数量'},
                color_discrete_map={'passed': '#28a745', 'failed': '#dc3545', 'skipped': '#ffc107'}
            )
            st.plotly_chart(fig_stack, use_container_width=True)
            
            # 数据表格
            st.subheader("📊 详细趋势数据")
            st.dataframe(df_trend, use_container_width=True)
        
    except Exception as e:
        st.error(f"生成趋势分析时出错: {e}")

def render_allure_report():
    """渲染Allure报告页面"""
    st.subheader("🔍 Allure报告")
    
    allure_dir = Path("./reports/allure")
    
    if not allure_dir.exists() or not list(allure_dir.glob("*-result.json")):
        st.info("暂无Allure报告数据，请先执行一些测试用例")
        return
    
    st.write("Allure报告文件已生成，您可以使用以下命令查看报告：")
    
    # 显示Allure命令
    st.code(f"""
# 安装Allure (如果尚未安装)
npm install -g allure-commandline

# 生成并打开Allure报告
allure serve {allure_dir.absolute()}
    """, language="bash")
    
    # 显示Allure文件列表
    allure_files = list(allure_dir.glob("*-result.json"))
    if allure_files:
        st.write(f"**找到 {len(allure_files)} 个Allure结果文件:**")
        
        for file in sorted(allure_files, reverse=True)[:10]:  # 显示最近10个
            file_time = datetime.fromtimestamp(file.stat().st_mtime)
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.write(f"📄 {file.name}")
            with col2:
                st.write(f"🕒 {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
            with col3:
                # 提供JSON文件下载
                with open(file, 'r', encoding='utf-8') as f:
                    json_content = f.read()
                
                st.download_button(
                    label="下载",
                    data=json_content,
                    file_name=file.name,
                    mime="application/json",
                    key=f"download_allure_{file.name}"
                )
    
    # Allure报告说明
    with st.expander("ℹ️ 关于Allure报告"):
        st.write("""
        **Allure报告特性:**
        - 📊 丰富的图表和统计信息
        - 📋 详细的测试步骤和附件
        - 🔍 强大的过滤和搜索功能
        - 📈 历史趋势分析
        - 📱 响应式设计，支持移动端
        
        **使用方法:**
        1. 确保已安装Node.js和npm
        2. 安装Allure命令行工具: `npm install -g allure-commandline`
        3. 运行命令: `allure serve ./reports/allure`
        4. 浏览器会自动打开Allure报告页面
        """)

def render_history_page(test_executor):
    """渲染历史记录页面"""
    st.header("📋 测试历史记录")
    
    try:
        # 获取历史记录
        history = asyncio.run(test_executor.get_test_history())
        
        if not history:
            st.info("暂无测试历史记录")
            return
        
        # 过滤选项
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # 状态过滤
            status_filter = st.multiselect(
                "按状态过滤",
                ['passed', 'failed', 'skipped'],
                default=['passed', 'failed', 'skipped']
            )
        
        with col2:
            # 测试名称过滤
            test_names = list(set(h.get('test_name', '') for h in history))
            name_filter = st.multiselect("按测试名称过滤", test_names)
        
        with col3:
            # 时间范围
            days_back = st.selectbox("时间范围", [7, 14, 30, 60, 90, 365], index=2)
        
        # 应用过滤
        filtered_history = history
        
        if status_filter:
            filtered_history = [h for h in filtered_history if h.get('status') in status_filter]
        
        if name_filter:
            filtered_history = [h for h in filtered_history if h.get('test_name') in name_filter]
        
        # 时间过滤
        cutoff_date = datetime.now() - timedelta(days=days_back)
        filtered_history = [
            h for h in filtered_history
            if datetime.fromisoformat(h.get('start_time', '')) >= cutoff_date
        ]
        
        st.write(f"显示 {len(filtered_history)} / {len(history)} 条记录")
        
        # 分页
        items_per_page = 20
        total_pages = (len(filtered_history) + items_per_page - 1) // items_per_page
        
        if total_pages > 1:
            page = st.selectbox("页码", range(1, total_pages + 1))
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_history = filtered_history[start_idx:end_idx]
        else:
            page_history = filtered_history
        
        # 显示历史记录
        for i, record in enumerate(page_history):
            status_icon = "✅" if record.get('status') == 'passed' else "❌" if record.get('status') == 'failed' else "⚠️"
            
            with st.expander(f"{status_icon} {record.get('test_name', 'Unknown Test')} - {record.get('start_time', '')[:19]}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**测试ID**: {record.get('test_id', 'N/A')}")
                    st.write(f"**状态**: {record.get('status', 'unknown')}")
                    st.write(f"**开始时间**: {record.get('start_time', 'N/A')}")
                    st.write(f"**结束时间**: {record.get('end_time', 'N/A')}")
                
                with col2:
                    st.write(f"**执行时间**: {record.get('duration', 0):.2f}s")
                    st.write(f"**描述**: {record.get('test_description', 'N/A')}")
                    
                    if record.get('tags'):
                        tags_html = " ".join([
                            f"<span style='background:#007bff;color:white;padding:2px 8px;border-radius:12px;font-size:0.8em;margin-right:5px;'>{tag}</span>"
                            for tag in record['tags']
                        ])
                        st.markdown(f"**标签**: {tags_html}", unsafe_allow_html=True)
                
                if record.get('error_message'):
                    st.error(f"**错误信息**: {record['error_message']}")
                
                # 显示步骤摘要
                steps = record.get('steps', [])
                if steps:
                    st.write(f"**步骤摘要** ({len(steps)} 个步骤):")
                    passed_steps = sum(1 for s in steps if s.get('status') == 'passed')
                    failed_steps = sum(1 for s in steps if s.get('status') == 'failed')
                    st.write(f"  ✅ 通过: {passed_steps} | ❌ 失败: {failed_steps}")
        
        # 导出功能
        if st.button("📥 导出历史记录"):
            df = pd.DataFrame(filtered_history)
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="下载CSV文件",
                data=csv,
                file_name=f"test_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
    except Exception as e:
        st.error(f"加载历史记录时出错: {e}")
