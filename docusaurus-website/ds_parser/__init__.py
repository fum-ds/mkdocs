# ds_parser/__init__.py
from .parser import DSCourseParser
from .generator import DocusaurusMarkdownGenerator
from .summary_generator import SummaryTableGenerator
from .models import Course

__version__ = "1.1.0"
__all__ = ['DSCourseParser', 'DocusaurusMarkdownGenerator', 'SummaryTableGenerator', 'Course']