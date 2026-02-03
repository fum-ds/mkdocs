# ds_parser/utils.py
import re
import pandas as pd
from typing import List, Dict
import datetime

def get_current_timestamp() -> str:
    """دریافت تاریخ و زمان فعلی به صورت فرمت شده"""
    now = datetime.datetime.now()
    
    # فرمت فارسی
    jalali_date = _convert_to_jalali(now)
    
    return f"{jalali_date} - {now.strftime('%H:%M')}"

def _convert_to_jalali(gregorian_date: datetime.datetime) -> str:
    """تبدیل تاریخ میلادی به شمسی (ساده شده)"""
    # در صورت نصب بودن jdatetime:
    try:
        import jdatetime
        jalali = jdatetime.datetime.fromgregorian(datetime=gregorian_date)
        return jalali.strftime("%Y/%m/%d")
    except ImportError:
        # اگر jdatetime نصب نیست، از تاریخ میلادی استفاده کن
        return gregorian_date.strftime("%Y/%m/%d")
    
def clean_text(text: str, keep_newlines: bool = False, remove_br: bool = True) -> str:
    """تمیز کردن متن از تگ‌های HTML و کاراکترهای اضافی"""
    if not text or pd.isna(text) or text == 'nan':
        return ''
    
    text = str(text)
    
    # حذف تگ‌های page
    text = re.sub(r'<div class="page"></div>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<div class="page">\s*</div>', '', text, flags=re.IGNORECASE)
    
    # حذف سایر تگ‌های HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    # حذف یا نگهداری <br>
    if remove_br:
        text = re.sub(r'<br\s*/?>', ' ', text)
    elif keep_newlines:
        text = re.sub(r'<br\s*/?>', '\n', text)
    else:
        text = re.sub(r'<br\s*/?>', ' ', text)
    
    # حذف کاراکترهای اضافی
    text = re.sub(r'[¢\*]', '', text)
    
    # اگر نباید newline نگه داریم
    if not keep_newlines:
        text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def remove_page_tag(text: str) -> str:
    """حذف تگ page از متن"""
    if not text:
        return text
    
    patterns = [
        r'<div class="page"></div>',
        r'<div class="page">\s*</div>',
        r'<div class=["\']page["\']></div>',
        r'<div class=["\']page["\']>\s*</div>'
    ]
    
    cleaned_text = text
    for pattern in patterns:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
    
    return cleaned_text.strip()

def create_filename(en_title: str) -> str:
    """ایجاد نام فایل از عنوان انگلیسی"""
    if not en_title or en_title == 'nan' or pd.isna(en_title):
        return ''
    
    en_title = str(en_title)
    filename = re.sub(r'[&]', 'and', en_title)
    filename = re.sub(r'[\s]', '-', filename)
    filename = re.sub(r'[^\w\-]', '', filename)
    
    return filename

def extract_section_content(lines: List[str], start_index: int, marker: str, next_markers: List[str], cleaner=clean_text) -> str:
    """استخراج محتوای یک بخش تا شروع بخش بعدی"""
    content_lines = []
    marker_found = False
    
    for i in range(start_index, len(lines)):
        current_line = lines[i]
        
        # اگر مارکر هدف را پیدا کردیم
        if marker in current_line and not marker_found:
            marker_found = True
            # متن بعد از مارکر را بگیر
            parts = current_line.split(marker, 1)
            if len(parts) > 1 and parts[1].strip():
                # حذف متن اضافی از انتهای خط
                clean_text_part = parts[1].strip()
                for next_marker in next_markers:
                    if next_marker in clean_text_part:
                        clean_text_part = clean_text_part.split(next_marker)[0].strip()
                        break
                if clean_text_part:
                    content_lines.append(clean_text_part)
            continue
        
        # اگر مارکر پیدا شده بود
        if marker_found:
            # بررسی کنیم آیا به بخش بعدی رسیده‌ایم
            is_next_section = False
            for next_marker in next_markers:
                if next_marker in current_line:
                    is_next_section = True
                    break
            
            # اگر به بخش بعدی رسیدیم، متوقف شو
            if is_next_section:
                break
            
            # اگر خط خالی یا جدول است، متوقف شو
            if not current_line.strip() or current_line.strip().startswith('|'):
                if '| # | # | # | # |' in current_line and len(current_line.split('|')) > 5:
                    break
                continue
            
            # خط را اضافه کن
            content_lines.append(current_line.strip())
    
    # حذف خطوط خالی انتهای لیست
    while content_lines and not content_lines[-1].strip():
        content_lines.pop()
    
    # ترکیب و پاکسازی
    combined_text = ' '.join(content_lines).strip()
    return cleaner(combined_text)

def split_course_sections(content: str) -> List[str]:
    """تقسیم محتوا به بخش‌های مختلف درس‌ها"""
    pattern = r'(\| # \| # \| # \| # \| # \|[\s\S]*?)(?=\| # \| # \| # \| # \| # \||\Z)'
    sections = re.findall(pattern, content)
    return [s.strip() for s in sections if s.strip()]