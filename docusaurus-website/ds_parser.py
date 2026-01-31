# ds_parser.py (فایل اصلی در ریشه پروژه)
#!/usr/bin/env python3
"""
پارسر برنامه درسی علوم داده - نسخه ماژولار
با قابلیت تولید جداول خلاصه
"""

import sys
from pathlib import Path

# اضافه کردن مسیر ماژول ds_parser به sys.path
sys.path.insert(0, str(Path(__file__).parent / 'ds_parser'))

from ds_parser.main import main

if __name__ == "__main__":
    df = main()