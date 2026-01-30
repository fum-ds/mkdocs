
import re
import pandas as pd
import os
from typing import List, Dict, Optional, Tuple

class DSCourseParser:
    """
    Parser جدید برای فایل‌های برنامه درسی علوم داده (DS-Chart.md)
    که با docx2md تبدیل شده‌اند.
    """
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.courses = []
        self.df = None
        
    def parse_file(self) -> pd.DataFrame:
        """پارس کردن فایل و استخراج اطلاعات درس‌ها"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # تقسیم محتوا به بخش‌های مختلف درس‌ها
        # در فرمت جدید، هر درس با یک جدول شروع می‌شود
        course_sections = self._split_course_sections(content)
        
        # پردازش هر بخش
        courses_data = []
        for section in course_sections:
            course_data = self._parse_course_section(section)
            if course_data and 'fa_title' in course_data:
                courses_data.append(course_data)
        
        # ایجاد DataFrame
        self._create_dataframe(courses_data)
        return self.df
    
    def _split_course_sections(self, content: str) -> List[str]:
        """تقسیم محتوا به بخش‌های مختلف درس‌ها"""
        # پیدا کردن شروع هر درس (جدول با 5 ستون)
        pattern = r'(\| # \| # \| # \| # \| # \|[\s\S]*?)(?=\| # \| # \| # \| # \| # \||\Z)'
        sections = re.findall(pattern, content)
        
        print(f"\n{'='*50}")
        print(f"تعداد بخش‌های پیدا شده: {len(sections)}")
        
        # نمایش اطلاعات هر بخش
        for i, section in enumerate(sections[:3]):  # فقط 3 بخش اول برای نمونه
            section_preview = section[:200].replace('\n', ' ')
            print(f"\nبخش {i+1} (اولین 200 کاراکتر):")
            print(f"  {section_preview}...")
            
            # بررسی وجود 'سرفصل درس' در بخش
            if 'سرفصل درس' in section:
                print(f"  ✓ شامل 'سرفصل درس'")
            else:
                print(f"  ✗ شامل 'سرفصل درس' نیست")
        
        return [s.strip() for s in sections if s.strip()]
    
    def _parse_course_section(self, section: str) -> Dict:
        """پارس کردن یک بخش درس"""
        lines = [l.rstrip() for l in section.split('\n')]  # فقط strip از راست
        course_data = {}
        
        in_table = False
        table_lines = []
        
        for i, original_line in enumerate(lines):
            line = original_line.strip()
            
            # تشخیص شروع جدول
            if line.startswith('|') and 'عنوان درس به فارسی:' in line:
                in_table = True
                table_lines.append(original_line)  # استفاده از خط اصلی
            elif in_table and line.startswith('|'):
                table_lines.append(original_line)
            elif in_table and not line.startswith('|'):
                in_table = False
                # پردازش جدول
                table_data = self._parse_table(table_lines)
                course_data.update(table_data)
                table_lines = []
            
            # فاز 2: استخراج اهداف و سرفصل
            # استفاده از خط اصلی برای جستجو
            if 'اهداف درس:' in original_line:
                course_data['goals'] = self._extract_text_after_marker(lines, 'اهداف درس:', start_index=i)
            
            if 'توانایی و شایستگی‌هایی که درس پرورش می‌دهد:' in original_line:
                course_data['competencies'] = self._extract_text_after_marker(lines, 'توانایی و شایستگی‌هایی که درس پرورش می‌دهد:', start_index=i)
            
            if 'سرفصل درس:' in original_line:
                course_data['syllabus'] = self._extract_syllabus(lines, line_index=i)
            
            if 'منابع:' in original_line:
                course_data['references'] = self._extract_references(lines, line_index=i)
        
        # پردازش باقی‌مانده
        if table_lines:
            table_data = self._parse_table(table_lines)
            course_data.update(table_data)
        
        return course_data

    def _parse_table(self, table_lines: List[str]) -> Dict:
            # دیباگ
        self.debug_table_parsing(table_lines)
        """پارس کردن جدول اطلاعات درس"""
        data = {}
        
        # اول، همه خطوط جدول را جمع‌آوری می‌کنیم
        all_table_data = []
        for line in table_lines:
            if not line.startswith('|'):
                continue
            all_table_data.append(line)
        
        # حالا همه خطوط را با هم بررسی می‌کنیم
        course_type_found = False
        unit_type_found = False
        
        for line in all_table_data:
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            
            # استخراج اطلاعات پایه
            if len(cells) >= 2:
                key = cells[0]
                value = cells[1] if len(cells) > 1 else ''
                
                key = self._clean_text(key)
                value = self._clean_text(value)
                
                key_mapping = {
                    'عنوان درس به فارسی:': 'fa_title',
                    'عنوان درس به انگلیسی:': 'en_title',
                    'دروس پیش‏نیاز:': 'prerequisites',
                    'دروس هم‏نیاز:': 'corequisites',
                    'تعداد واحد:': 'units',
                    'تعداد ساعت:': 'hours',
                    'حل تمرین دارد': 'has_exercises'
                }
                
                if key in key_mapping:
                    mapped_key = key_mapping[key]
                    
                    if mapped_key == 'has_exercises':
                        data[mapped_key] = 'دارد' if value else 'ندارد'
                    elif mapped_key in ['prerequisites', 'corequisites']:
                        data[mapped_key] = value if value else 'ندارد'
                    else:
                        data[mapped_key] = value
            
            # استخراج نوع درس - فقط از سطرهای خاص
            if any(x in line for x in ['پایه', 'تخصصی الزامی', 'تخصصی اختیاری', 'مهارتی']):
                # فقط سطرهای مربوط به "نوع درس و واحد" را بررسی کن
                if 'نوع درس و واحد' not in line:  # این سطر عنوان است
                    for i, cell in enumerate(cells):
                        cell_clean = self._clean_text(cell)
                        
                        # اولویت‌بندی: پایه > تخصصی الزامی > تخصصی اختیاری > مهارتی
                        if not course_type_found:
                            if 'پایه' in cell_clean and 'n' in cell_clean:
                                data['course_type'] = 'پایه'
                                course_type_found = True
                            elif 'تخصصی الزامی' in cell_clean:
                                data['course_type'] = 'تخصصی الزامی'
                                course_type_found = True
                            elif 'تخصصی اختیاری' in cell_clean:
                                data['course_type'] = 'تخصصی اختیاری'
                                course_type_found = True
                            elif 'مهارتی' in cell_clean and '£' in cell_clean:
                                data['course_type'] = 'مهارتی'
                                course_type_found = True
            
            # استخراج نوع واحد
            if any(x in line for x in ['نظری', 'عملی', 'نظری-عملی']):
                if not unit_type_found:
                    for cell in cells:
                        cell_clean = self._clean_text(cell)
                        if 'نظریn' in cell_clean:
                            data['unit_type'] = 'نظری'
                            unit_type_found = True
                        elif 'عملی £' in cell_clean:
                            data['unit_type'] = 'عملی'
                            unit_type_found = True
                        elif 'نظری-عملی £' in cell_clean:
                            data['unit_type'] = 'نظری-عملی'
                            unit_type_found = True
        
        # مقادیر پیش‌فرض اگر پیدا نشدند
        if 'course_type' not in data:
            data['course_type'] = ''
        if 'unit_type' not in data:
            data['unit_type'] = 'نظری'
        
        return data

    def _extract_text_after_marker(self, lines: List[str], marker: str, start_index: int = 0, max_lines: int = 10) -> str:
        """استخراج متن بعد از یک مارکر خاص"""
        result = []
        found = False
        count = 0
        
        for i in range(start_index, len(lines)):
            line = lines[i].strip()
            
            if marker in lines[i]:  # بررسی در خط اصلی
                found = True
                # استخراج متن بعد از مارکر
                parts = lines[i].split(marker, 1)
                if len(parts) > 1 and parts[1].strip():
                    result.append(parts[1].strip())
                continue
            
            if found:
                if line and not line.startswith('|'):
                    result.append(line)
                    count += 1
                    if count >= max_lines:
                        break
                elif line and line.startswith('|'):
                    break
        
        return ' '.join(result).strip()

    def _extract_syllabus(self, lines: List[str], line_index: int) -> List[str]:
        """استخراج سرفصل درس"""
        syllabus_lines = []
        in_syllabus = False
        
        for i in range(line_index, len(lines)):
            line = lines[i].strip()
            
            if 'سرفصل درس:' in lines[i]:  # بررسی در خط اصلی
                in_syllabus = True
                # حذف مارکر از خط
                clean_line = lines[i].replace('سرفصل درس:', '').strip()
                if clean_line:
                    syllabus_lines.append(clean_line)
                continue
            
            if in_syllabus:
                # توقف وقتی به بخش بعدی می‌رسیم
                if ('راهبردهای تدریس' in line or 
                    'روش یاددهی' in line or 
                    'روش ارزیابی' in line or
                    'تجهیزات' in line or
                    'منابع:' in lines[i] or  # بررسی در خط اصلی
                    line.startswith('|') and '|' in line and line.count('|') >= 3):
                    break
                
                if line:
                    syllabus_lines.append(line)
        
        # حذف خطوط خالی و یکسان‌سازی
        syllabus_lines = [self._clean_text(line) for line in syllabus_lines if line.strip()]
        return syllabus_lines
    
    def _extract_references(self, lines: List[str], line_index: int) -> List[str]:
        """استخراج منابع"""
        ref_lines = []
        
        for i in range(line_index + 1, len(lines)):
            line = lines[i].strip()
            
            # توقف وقتی به درس بعدی می‌رسیم
            if line.startswith('| # | # | # | # | # |') or 'عنوان درس به فارسی:' in line:
                break
            
            if line and not line.startswith('<div'):
                ref_lines.append(self._clean_text(line))
        
        return ref_lines
    
    def _clean_text(self, text: str) -> str:
        """تمیز کردن متن از تگ‌های HTML و کاراکترهای اضافی"""
        if not text:
            return ''
        
        # حذف تگ‌های HTML
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'<br\s*/?>', ' ', text)
        
        # حذف کاراکترهای خاص (اما n و £ را برای تشخیص نوع درس نگه می‌داریم)
        # ابتدا متن اصلی را کپی می‌کنیم
        clean_for_display = text
        
        # برای تشخیص نوع درس، n و £ را نگه می‌داریم
        clean_for_display = re.sub(r'[¢\*]', '', clean_for_display)
        
        # حذف فاصله‌های اضافی
        clean_for_display = re.sub(r'\s+', ' ', clean_for_display)
        
        return clean_for_display.strip()
    
    def _create_dataframe(self, courses_data: List[Dict]):
        """ایجاد DataFrame از داده‌های استخراج شده"""
        # تعریف ستون‌ها
        columns = [
            'fa_title', 'en_title', 'prerequisites', 'corequisites',
            'units', 'hours', 'has_exercises', 'course_type', 'unit_type',
            'goals', 'competencies', 'syllabus', 'references'
        ]
        
        # تبدیل لیست دیکشنری‌ها به DataFrame
        df = pd.DataFrame(courses_data, columns=columns)
        
        # پر کردن مقادیر NaN
        df.fillna({
            'prerequisites': 'ندارد',
            'corequisites': 'ندارد',
            'has_exercises': '',
            'course_type': '',
            'unit_type': 'نظری',
            'goals': '',
            'competencies': '',
            'syllabus': '',
            'references': ''
        }, inplace=True)
        
        # اضافه کردن ستون‌های محاسباتی
        df['en_file_name'] = df['en_title'].apply(self._create_filename)
        df['c_cat'] = df['course_type']
        
        self.df = df
        return self.df
    
    def _create_filename(self, en_title: str) -> str:
        """ایجاد نام فایل از عنوان انگلیسی"""
        if not en_title:
            return ''
        
        # جایگزینی کاراکترهای خاص
        filename = re.sub(r'[&]', 'and', en_title)
        filename = re.sub(r'[\s]', '-', filename)
        filename = re.sub(r'[^\w\-]', '', filename)
        
        return filename
    
    def get_courses_by_type(self, course_type: str) -> pd.DataFrame:
        """دریافت درس‌ها بر اساس نوع"""
        if self.df is None:
            self.parse_file()
        
        return self.df[self.df['course_type'] == course_type].copy()

    def debug_table_parsing(self, table_lines: List[str]):
        """دیباگ پارس کردن جدول"""
        print("\n" + "="*50)
        print("دیباگ پارس جدول:")
        print("="*50)
        
        for i, line in enumerate(table_lines):
            print(f"\nخط {i}: {repr(line[:100])}")
            
            if 'پایه' in line or 'تخصصی' in line or 'مهارتی' in line:
                print(f"  ← این خط حاوی اطلاعات نوع درس است")
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                for j, cell in enumerate(cells):
                    print(f"    سلول {j}: {repr(cell)}")
                    if 'پایه' in cell:
                        print(f"      ✓ پایه یافت شد")
                    if 'تخصصی الزامی' in cell:
                        print(f"      ✓ تخصصی الزامی یافت شد")
                    if 'تخصصی اختیاری' in cell:
                        print(f"      ✓ تخصصی اختیاری یافت شد")
                    if 'مهارتی' in cell:
                        print(f"      ✓ مهارتی یافت شد")
        
        # حالا regex را تست می‌کنیم
        table_content = '\n'.join(table_lines)
        print(f"\nجستجوی regex در کل جدول:")
        
        type_patterns = [
            (r'پایه n', 'پایه'),
            (r'تخصصی الزامی£', 'تخصصی الزامی'),
            (r'تخصصی اختیاری £', 'تخصصی اختیاری'),
            (r'مهارتی / اشتغال‌پذیری £', 'مهارتی')
        ]
        
        for pattern, name in type_patterns:
            if re.search(pattern, table_content):
                print(f"  ✓ {name} با الگوی {pattern}")
            else:
                print(f"  ✗ {name} با الگوی {pattern}")

class DocusaurusMarkdownGenerator:
    """تولید کننده فایل‌های Markdown برای Docusaurus"""
    
    def __init__(self, base_path: str = './docs/curriculum/'):
        self.base_path = base_path
        self.subfolders = {
            'پایه': 'base',
            'تخصصی الزامی': 'mandatory',
            'تخصصی اختیاری': 'elective',
            'مهارتی': 'skill'
        }
    
    def generate_files(self, df: pd.DataFrame):
        """تولید فایل‌های Markdown برای همه درس‌ها"""
        # مرتب‌سازی بر اساس نوع درس و عنوان فارسی
        df['fa_title_sort'] = df['fa_title'].str.replace('گ', 'ك').str.replace('پ', 'ب')
        df['position'] = df.groupby('course_type')['fa_title_sort'].rank(method='first')
        
        # پاکسازی پوشه‌های قبلی
        self._clear_folders()
        
        # ایجاد فایل برای هر درس
        for _, row in df.iterrows():
            self._generate_course_file(row)
    
    def _generate_course_file(self, row):
        """ایجاد فایل Markdown برای یک درس"""
        # تعیین مسیر بر اساس نوع درس
        course_type = row['course_type']
        folder = self.subfolders.get(course_type, 'other')
        file_path = os.path.join(self.base_path, folder, f"{row['en_file_name']}.md")
        
        # ایجاد پوشه اگر وجود ندارد
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # ایجاد محتوای فایل
        content = self._create_file_content(row, folder)
        
        # نوشتن در فایل
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_file_content(self, row, folder: str) -> str:
        """ایجاد محتوای فایل Markdown"""
        lines = []
        
        # Frontmatter برای Docusaurus
        lines.append('---')
        lines.append(f"sidebar_position: {int(row['position'])}")
        lines.append('---')
        lines.append('')
        
        # عنوان فارسی
        lines.append(f"# {row['fa_title']}")
        lines.append('')
        
        # عنوان انگلیسی
        lines.append(f"## {row['en_title']}")
        lines.append('')
        
        # جداکننده
        lines.append('---')
        lines.append('')
        
        # اطلاعات درس
        lines.append('### اطلاعات درس')
        lines.append('')
        
        # ایجاد جدول اطلاعات
        info_table = [
            ['نام درس:', row['fa_title'], 'مقطع:', 'کارشناسی'],
            ['پیش‌نیاز:', self._format_prerequisites(row['prerequisites']), 
             'گروه درس:', row['course_type']],
            ['هم‌نیاز:', row['corequisites'], 
             'نوع درس:', row['unit_type']],
            ['تعداد واحد:', row['units'], 
             'تعداد ساعت:', row['hours']],
            ['حل تمرین:', row['has_exercises'], '', '']
        ]
        
        # تبدیل جدول به Markdown
        table_md = self._create_markdown_table(info_table)
        lines.append(table_md)
        lines.append('')
        
        # اهداف درس
        if row['goals']:
            lines.append('### اهداف درس')
            lines.append('')
            lines.append(row['goals'])
            lines.append('')
        
        # شایستگی‌ها
        if row['competencies']:
            lines.append('### توانایی‌ها و شایستگی‌ها')
            lines.append('')
            lines.append(row['competencies'])
            lines.append('')
        
        # سرفصل
        lines.append('### سرفصل درس')
        lines.append('')
        if isinstance(row['syllabus'], list):
            for item in row['syllabus']:
                lines.append(f"- {item}")
        else:
            lines.append(row['syllabus'])
        lines.append('')
        
        # منابع
        lines.append('### منابع')
        lines.append('')
        if isinstance(row['references'], list):
            for ref in row['references']:
                lines.append(f"- {ref}")
        else:
            lines.append(row['references'])
        
        return '\n'.join(lines)
    
    def _format_prerequisites(self, prereq_str: str) -> str:
        """فرمت‌بندی پیش‌نیازها (در این نسخه ساده)"""
        # در نسخه کامل می‌توانید لینک‌سازی اضافه کنید
        return prereq_str
    
    def _create_markdown_table(self, data: List[List[str]]) -> str:
        """ایجاد جدول Markdown از داده‌های دو بعدی"""
        if not data:
            return ''
        
        # ایجاد سرستون‌ها
        headers = ['', '', '', '']
        separator = ['---', '---', '---', '---']
        
        # تبدیل به رشته
        table_lines = []
        table_lines.append('| ' + ' | '.join(headers) + ' |')
        table_lines.append('| ' + ' | '.join(separator) + ' |')
        
        for row in data:
            table_lines.append('| ' + ' | '.join(row) + ' |')
        
        return '\n'.join(table_lines)
    
    def _clear_folders(self):
        """پاکسازی پوشه‌های خروجی"""
        for folder in self.subfolders.values():
            dir_path = os.path.join(self.base_path, folder)
            if os.path.exists(dir_path):
                for file in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, file)
                    if os.path.isfile(file_path) and file != '_category_.json':
                        os.remove(file_path)

def main():
    """تابع اصلی اجرای برنامه"""
    # 1. پارس کردن فایل DS-Chart.md
    parser = DSCourseParser('../input/DS-Chart.md')
    df = parser.parse_file()
    
    print(f"تعداد درس‌های استخراج شده: {len(df)}")
    print(f"انواع درس‌ها: {df['course_type'].unique().tolist()}")
    
    # 2. تولید فایل‌های Markdown
    generator = DocusaurusMarkdownGenerator('./docs/curriculum/')
    generator.generate_files(df)
    
    print("فایل‌های Markdown با موفقیت تولید شدند.")
    
    # 3. نمایش نمونه‌ای از داده‌ها
    print("\nنمونه‌ای از داده‌های استخراج شده:")
    print(df[['fa_title', 'en_title', 'course_type', 'units']].head())
    
    return df

if __name__ == "__main__":
    df = main()