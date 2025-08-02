"""
Core module for the frontend automation test platform
"""

from .test_case_manager import TestCaseManager, TestCase
from .strands_test_executor import StrandsTestExecutor
from .mock_strands_executor import MockStrandsTestExecutor
from .report_generator import ReportGenerator

__all__ = ['TestCaseManager', 'TestCase', 'StrandsTestExecutor', 'MockStrandsTestExecutor', 'ReportGenerator']
