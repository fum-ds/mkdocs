import re
import pandas as pd
import os
import numpy as np
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
        
        print(f"📖 File size: {len(content)} characters")
        
        # تقسیم محتوا به بخش‌های مختلف درس‌ها
        course_sections = self._split_course_sections(content)
        print(f"📚 Found {len(course_sections)} course sections")
        
        # پردازش هر بخش
        courses_data = []
        for i, section in enumerate(course_sections[:2]):  # فقط 2 بخش اول برای دیباگ
            print(f"\n{'='*60}")
            print(f"📋 Processing course section {i+1}/{len(course_sections)}")
            print('='*60)
            course_data = self._parse_course_section(section)
            if course_data:
                print(f"✅ Extracted data: {course_data.get('fa_title', 'NO TITLE')}")
                if 'fa_title' in course_data:
                    courses_data.append(course_data)
        
        # بقیه بخش‌ها
        for i, section in enumerate(course_sections[2:]):
            course_data = self._parse_course_section(section)
            if course_data and 'fa_title' in course_data:
                courses_data.append(course_data)
        
        print(f"\n📦 Total courses extracted: {len(courses_data)}")
        
        # ایجاد DataFrame
        self._create_dataframe(courses_data)
        return self.df
    
    def _split_course_sections(self, content: str) -> List[str]:
        """تقسیم محتوا به بخش‌های مختلف درس‌ها"""
        # پیدا کردن شروع هر درس (جدول با 5 ستون)
        pattern = r'(\| # \| # \| # \| # \| # \|[\s\S]*?)(?=\| # \| # \| # \| # \| # \||\Z)'
        sections = re.findall(pattern, content)
        return [s.strip() for s in sections if s.strip()]
    
    def _parse_course_section(self, section: str) -> Dict:
        """پارس کردن یک بخش درس"""
        lines = [l.rstrip() for l in section.split('\n')]
        course_data = {}
        
        in_table = False
        table_lines = []
        
        for i, original_line in enumerate(lines):
            line = original_line.strip()
            
            # تشخیص شروع جدول
            if line.startswith('|') and ('عنوان درس به فارسی:' in line or '|عنوان درس به فارسی:' in original_line):
                in_table = True
                table_lines.append(original_line)
            elif in_table and line.startswith('|'):
                table_lines.append(original_line)
            elif in_table and not line.startswith('|'):
                in_table = False
                table_data = self._parse_table(table_lines)
                course_data.update(table_data)
                table_lines = []
            
            # استخراج اهداف و سرفصل
            if 'اهداف درس:' in original_line:
                course_data['goals'] = self._extract_text_after_marker(lines, 'اهداف درس:', start_index=i)
            
            if 'توانایی و شایستگی‌هایی که درس پرورش می‌دهد:' in original_line:
                course_data['competencies'] = self._extract_text_after_marker(
                    lines, 'توانایی و شایستگی‌هایی که درس پرورش می‌دهد:', start_index=i)
            
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
        """پارس کردن جدول اطلاعات درس"""
        data = {}
        
        print(f"\n📊 Parsing table with {len(table_lines)} lines")
        
        # متصل کردن همه خطوط
        full_table_text = '\n'.join(table_lines)
        
        # 🔧 **استخراج اطلاعات با روش ساده‌تر**
        # خط به خط بررسی می‌کنیم
        
        for line in table_lines:
            if not line.startswith('|'):
                continue
            
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            
            # 🔍 **یافتن عنوان فارسی**
            for i, cell in enumerate(cells):
                if 'عنوان درس به فارسی:' in cell:
                    if i + 1 < len(cells):
                        fa_title = cells[i + 1]
                        data['fa_title'] = self._clean_text(fa_title)
                        print(f"✅ Found Persian title: {data['fa_title']}")
                    break
            
            # 🔍 **یافتن عنوان انگلیسی**
            for i, cell in enumerate(cells):
                if 'عنوان درس به انگلیسی:' in cell:
                    if i + 1 < len(cells):
                        en_title = cells[i + 1]
                        data['en_title'] = self._clean_text(en_title)
                        print(f"✅ Found English title: {data['en_title']}")
                    break
            
            # 🔍 **یافتن پیش‌نیازها**
            for i, cell in enumerate(cells):
                if 'دروس پیش‏نیاز:' in cell:
                    if i + 1 < len(cells):
                        prereq = cells[i + 1]
                        data['prerequisites'] = self._clean_text(prereq) if prereq else 'ندارد'
                    break
            
            # 🔍 **یافتن هم‌نیازها**
            for i, cell in enumerate(cells):
                if 'دروس هم‏نیاز:' in cell:
                    if i + 1 < len(cells):
                        coreq = cells[i + 1]
                        data['corequisites'] = self._clean_text(coreq) if coreq else 'ندارد'
                    break
            
            # 🔍 **یافتن تعداد واحد**
            for i, cell in enumerate(cells):
                if 'تعداد واحد:' in cell:
                    if i + 1 < len(cells):
                        units = cells[i + 1]
                        # جدا کردن "حل تمرین دارد" از تعداد واحد
                        if 'حل تمرین دارد' in units:
                            units = units.replace('حل تمرین دارد', '').strip()
                            data['has_exercises'] = 'دارد'
                        data['units'] = self._clean_text(units)
                    break
            
            # 🔍 **یافتن تعداد ساعت**
            for i, cell in enumerate(cells):
                if 'تعداد ساعت:' in cell:
                    if i + 1 < len(cells):
                        hours = cells[i + 1]
                        data['hours'] = self._clean_text(hours)
                    break
        
        # 🔧 **اگر هنوز حل تمرین مشخص نشده**
        if 'has_exercises' not in data:
            if 'حل تمرین دارد' in full_table_text:
                data['has_exercises'] = 'دارد'
            elif 'حل تمرین ندارد' in full_table_text:
                data['has_exercises'] = 'ندارد'
            else:
                data['has_exercises'] = ''
        
        # 🔧 **تشخیص نوع درس**
        course_type = ''
        unit_type = 'نظری'
        
        # ابتدا به دنبال n می‌گردیم (مربع توپر)
        for line in table_lines:
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            
            for cell in cells:
                if 'n' in cell:  # مربع توپر
                    if 'پایه' in cell:
                        course_type = 'پایه'
                    elif 'تخصصی الزامی' in cell:
                        course_type = 'تخصصی الزامی'
                    elif 'تخصصی اختیاری' in cell:
                        course_type = 'تخصصی اختیاری'
                    elif 'مهارتی' in cell:
                        course_type = 'مهارتی'
                    
                    if 'نظری' in cell:
                        unit_type = 'نظری'
                    elif 'عملی' in cell:
                        unit_type = 'عملی'
                    elif 'نظری-عملی' in cell:
                        unit_type = 'نظری-عملی'
        
        # اگر n پیدا نشد، به دنبال سلول‌های بدون £ می‌گردیم (بدون مربع توخالی)
        if not course_type:
            for line in table_lines:
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                
                for cell in cells:
                    if '£' not in cell:  # مربع توخالی ندارد
                        if 'پایه' in cell and 'n' not in cell:
                            course_type = 'پایه'
                        elif 'تخصصی الزامی' in cell and 'n' not in cell:
                            course_type = 'تخصصی الزامی'
                        elif 'تخصصی اختیاری' in cell and 'n' not in cell:
                            course_type = 'تخصصی اختیاری'
                        elif 'مهارتی' in cell and 'n' not in cell:
                            course_type = 'مهارتی'
        
        data['course_type'] = course_type if course_type else ''
        data['unit_type'] = unit_type if unit_type else 'نظری'
        
        # دیباگ
        print(f"📝 Course type: {data.get('course_type', 'NOT FOUND')}")
        print(f"📝 Unit type: {data.get('unit_type', 'NOT FOUND')}")
        
        return data

    def _extract_text_after_marker(self, lines: List[str], marker: str, start_index: int = 0, max_lines: int = 10) -> str:
        """استخراج متن بعد از یک مارکر خاص"""
        result = []
        found = False
        count = 0
        
        for i in range(start_index, len(lines)):
            line = lines[i].strip()
            
            if marker in lines[i]:
                found = True
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
            
            if 'سرفصل درس:' in lines[i]:
                in_syllabus = True
                clean_line = lines[i].replace('سرفصل درس:', '').strip()
                if clean_line:
                    syllabus_lines.append(clean_line)
                continue
            
            if in_syllabus:
                if ('راهبردهای تدریس' in line or 
                    'روش یاددهی' in line or 
                    'روش ارزیابی' in line or
                    'تجهیزات' in line or
                    'منابع:' in lines[i] or
                    line.startswith('|') and '|' in line and line.count('|') >= 3):
                    break
                
                if line:
                    syllabus_lines.append(line)
        
        syllabus_lines = [self._clean_text(line) for line in syllabus_lines if line.strip()]
        return syllabus_lines
    
    def _extract_references(self, lines: List[str], line_index: int) -> List[str]:
        """استخراج منابع"""
        ref_lines = []
        
        for i in range(line_index + 1, len(lines)):
            line = lines[i].strip()
            
            if line.startswith('| # | # | # | # | # |') or 'عنوان درس به فارسی:' in line:
                break
            
            if line and not line.startswith('<div'):
                ref_lines.append(self._clean_text(line))
        
        return ref_lines
    
    def _clean_text(self, text: str) -> str:
        """تمیز کردن متن از تگ‌های HTML و کاراکترهای اضافی"""
        if not text or pd.isna(text) or text == 'nan':
            return ''
        
        text = str(text)
        
        # حذف تگ‌های HTML
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'<br\s*/?>', ' ', text)
        
        # حذف کاراکترهای اضافی (اما n و £ را نگه می‌داریم)
        text = re.sub(r'[¢\*]', '', text)
        
        # حذف فاصله‌های اضافی
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _create_dataframe(self, courses_data: List[Dict]):
        """ایجاد DataFrame از داده‌های استخراج شده"""
        if not courses_data:
            print("❌ No course data extracted!")
            self.df = pd.DataFrame()
            return self.df
        
        columns = [
            'fa_title', 'en_title', 'prerequisites', 'corequisites',
            'units', 'hours', 'has_exercises', 'course_type', 'unit_type',
            'goals', 'competencies', 'syllabus', 'references'
        ]
        
        # فقط دیکشنری‌هایی که fa_title دارند
        valid_courses = [course for course in courses_data if 'fa_title' in course and course['fa_title']]
        
        print(f"\n📊 Creating DataFrame from {len(valid_courses)} valid courses")
        
        df = pd.DataFrame(valid_courses, columns=columns)
        
        # پر کردن مقادیر خالی
        for col in columns:
            if col not in df.columns:
                df[col] = ''
        
        # مقادیر پیش‌فرض
        df = df.fillna('')
        
        default_values = {
            'prerequisites': 'ندارد',
            'corequisites': 'ندارد',
            'has_exercises': '',
            'course_type': '',
            'unit_type': 'نظری',
            'goals': '',
            'competencies': '',
            'syllabus': '',
            'references': ''
        }
        
        for col, default_val in default_values.items():
            if col in df.columns:
                df[col] = df[col].apply(lambda x: default_val if not x else x)
        
        # ایجاد نام فایل
        df['en_file_name'] = df['en_title'].apply(self._create_filename)
        df['c_cat'] = df['course_type']
        
        # اطمینان از string بودن
        for col in df.columns:
            df[col] = df[col].astype(str)
        
        self.df = df
        
        # نمایش آمار
        print(f"\n📈 Extraction Statistics:")
        print(f"Total valid courses: {len(df)}")
        
        if len(df) > 0:
            print(f"\n📊 Course types distribution:")
            print(df['course_type'].value_counts())
            
            print(f"\n📊 Has exercises distribution:")
            print(df['has_exercises'].value_counts())
            
            # نمایش چند نمونه
            print(f"\n📋 Sample data (first 5):")
            print(df[['fa_title', 'en_title', 'course_type', 'units', 'has_exercises']].head())
        
        return self.df
    
    def _create_filename(self, en_title: str) -> str:
        """ایجاد نام فایل از عنوان انگلیسی"""
        if not en_title or en_title == 'nan' or pd.isna(en_title):
            return ''
        
        en_title = str(en_title)
        # حذف کاراکترهای خاص
        filename = re.sub(r'[&]', 'and', en_title)
        filename = re.sub(r'[\s]', '-', filename)
        filename = re.sub(r'[^\w\-]', '', filename)
        
        return filename
    
    def get_courses_by_type(self, course_type: str) -> pd.DataFrame:
        """دریافت درس‌ها بر اساس نوع"""
        if self.df is None:
            self.parse_file()
        
        return self.df[self.df['course_type'] == course_type].copy()


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
        self.course_mapping = {}
    
    def generate_files(self, df: pd.DataFrame):
        """تولید فایل‌های Markdown برای همه درس‌ها"""
        if df is None or len(df) == 0:
            print("❌ No data to generate files!")
            return
        
        print(f"\n🎯 Generating files for {len(df)} courses...")
        
        # اطمینان از string بودن مقادیر
        df = df.fillna('')
        
        # ایجاد نگاشت عنوان فارسی به نام فایل
        valid_mappings = 0
        for _, row in df.iterrows():
            fa_title = str(row['fa_title']).strip()
            en_file_name = str(row['en_file_name']).strip()
            course_type = str(row['course_type']).strip()
            
            if fa_title and fa_title != 'nan' and en_file_name:
                self.course_mapping[fa_title] = {
                    'file_name': en_file_name,
                    'course_type': course_type
                }
                valid_mappings += 1
        
        print(f"📚 Created {valid_mappings} course mappings")
        
        # مرتب‌سازی بر اساس نوع درس
        df['position'] = 0
        position_counter = {}
        
        for _, row in df.iterrows():
            course_type = str(row['course_type']).strip()
            if not course_type or course_type == 'nan':
                course_type = 'other'
            
            if course_type not in position_counter:
                position_counter[course_type] = 1
            else:
                position_counter[course_type] += 1
            
            df.loc[df.index[_], 'position'] = position_counter[course_type]
        
        self._clear_folders()
        
        # ایجاد فایل برای هر درس
        generated_count = 0
        for _, row in df.iterrows():
            if self._generate_course_file(row):
                generated_count += 1
        
        print(f"\n✅ Successfully generated {generated_count} files")
        
        # نمایش خلاصه
        print(f"\n📁 Files generated in folders:")
        for course_type, folder in self.subfolders.items():
            folder_path = os.path.join(self.base_path, folder)
            if os.path.exists(folder_path):
                files = [f for f in os.listdir(folder_path) if f.endswith('.md')]
                if files:
                    print(f"  📂 {folder}/: {len(files)} files")
        
        # دروس other
        other_path = os.path.join(self.base_path, 'other')
        if os.path.exists(other_path):
            files = [f for f in os.listdir(other_path) if f.endswith('.md')]
            if files:
                print(f"  📂 other/: {len(files)} files (no type detected)")
    
    def _generate_course_file(self, row) -> bool:
        """ایجاد فایل Markdown برای یک درس"""
        try:
            fa_title = str(row['fa_title']).strip()
            en_file_name = str(row['en_file_name']).strip()
            course_type = str(row['course_type']).strip()
            
            if not fa_title or fa_title == 'nan' or not en_file_name or en_file_name == 'nan':
                print(f"⚠️  Skipping: Empty title or filename")
                return False
            
            folder = self.subfolders.get(course_type, 'other')
            file_path = os.path.join(self.base_path, folder, f"{en_file_name}.md")
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            content = self._create_file_content(row, folder)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✓ Created: {folder}/{en_file_name}.md")
            return True
            
        except Exception as e:
            print(f"❌ Error creating file for {row.get('fa_title', 'Unknown')}: {str(e)}")
            return False
    
    def _create_file_content(self, row, folder: str) -> str:
        """ایجاد محتوای فایل Markdown"""
        # تبدیل همه مقادیر به string
        position = int(float(str(row['position']))) if str(row['position']).replace('.', '').isdigit() else 1
        fa_title = str(row['fa_title']).strip()
        en_title = str(row['en_title']).strip() if str(row['en_title']).strip() != 'nan' else ''
        prerequisites = str(row['prerequisites']).strip() if str(row['prerequisites']).strip() != 'nan' else 'ندارد'
        corequisites = str(row['corequisites']).strip() if str(row['corequisites']).strip() != 'nan' else 'ندارد'
        course_type = str(row['course_type']).strip() if str(row['course_type']).strip() != 'nan' else ''
        unit_type = str(row['unit_type']).strip() if str(row['unit_type']).strip() != 'nan' else 'نظری'
        units = str(row['units']).strip() if str(row['units']).strip() != 'nan' else ''
        hours = str(row['hours']).strip() if str(row['hours']).strip() != 'nan' else ''
        has_exercises = str(row['has_exercises']).strip() if str(row['has_exercises']).strip() != 'nan' else ''
        goals = str(row['goals']).strip() if str(row['goals']).strip() != 'nan' else ''
        competencies = str(row['competencies']).strip() if str(row['competencies']).strip() != 'nan' else ''
        syllabus = row['syllabus']
        references = row['references']
        
        lines = []
        
        # Frontmatter
        lines.append('---')
        lines.append(f"sidebar_position: {position}")
        lines.append('---')
        lines.append('')
        
        # عنوان فارسی
        lines.append(f"# {fa_title}")
        lines.append('')
        
        # عنوان انگلیسی
        if en_title:
            lines.append(f"## {en_title}")
            lines.append('')
        
        # جداکننده
        lines.append('---')
        lines.append('')
        
        # اطلاعات درس
        lines.append('### اطلاعات درس')
        lines.append('')
        
        # فرمت‌بندی پیش‌نیازها
        prereq_formatted = self._format_prerequisites(prerequisites, fa_title)
        coreq_formatted = self._format_prerequisites(corequisites, fa_title)
        
        # ایجاد جدول
        info_table = [
            ['نام درس:', fa_title, 'مقطع:', 'کارشناسی'],
            ['پیش‌نیاز:', prereq_formatted, 'گروه درس:', course_type],
            ['هم‌نیاز:', coreq_formatted, 'نوع درس:', unit_type],
            ['تعداد واحد:', units, 'تعداد ساعت:', hours],
            ['حل تمرین:', has_exercises, '', '']
        ]
        
        # پاکسازی جدول
        clean_table = []
        for row_data in info_table:
            clean_row = []
            for cell in row_data:
                if cell is None:
                    clean_row.append('')
                else:
                    clean_row.append(str(cell).strip())
            clean_table.append(clean_row)
        
        table_md = self._create_markdown_table(clean_table)
        lines.append(table_md)
        lines.append('')
        
        # اهداف درس
        if goals and goals != 'ندارد':
            lines.append('### اهداف درس')
            lines.append('')
            lines.append(goals)
            lines.append('')
        
        # شایستگی‌ها
        if competencies and competencies != 'ندارد':
            lines.append('### توانایی‌ها و شایستگی‌ها')
            lines.append('')
            lines.append(competencies)
            lines.append('')
        
        # سرفصل
        lines.append('### سرفصل درس')
        lines.append('')
        if isinstance(syllabus, list) and syllabus:
            for item in syllabus:
                if item and str(item).strip() and str(item).strip() != 'nan':
                    lines.append(f"- {str(item).strip()}")
        elif syllabus and str(syllabus).strip() and str(syllabus).strip() != 'nan':
            lines.append(str(syllabus).strip())
        else:
            lines.append('(سرفصل تعیین نشده است)')
        lines.append('')
        
        # منابع
        lines.append('### منابع')
        lines.append('')
        if isinstance(references, list) and references:
            for ref in references:
                if ref and str(ref).strip() and str(ref).strip() != 'nan':
                    lines.append(f"- {str(ref).strip()}")
        elif references and str(references).strip() and str(references).strip() != 'nan':
            lines.append(str(references).strip())
        else:
            lines.append('(منابع تعیین نشده است)')
        
        return '\n'.join(lines)
    
    def _format_prerequisites(self, prereq_str: str, current_course: str = '') -> str:
        """فرمت‌بندی پیش‌نیازها با لینک"""
        if not prereq_str or prereq_str == 'ندارد' or prereq_str == 'nan':
            return 'ندارد'
        
        prereq_str = str(prereq_str)
        
        # تقسیم پیش‌نیازها
        prereqs = []
        if '،' in prereq_str:
            prereqs = [p.strip() for p in prereq_str.split('،') if p.strip()]
        elif ',' in prereq_str:
            prereqs = [p.strip() for p in prereq_str.split(',') if p.strip()]
        else:
            prereqs = [prereq_str.strip()]
        
        linked_prereqs = []
        for prereq in prereqs:
            if prereq in self.course_mapping:
                course_info = self.course_mapping[prereq]
                folder = self.subfolders.get(course_info['course_type'], 'other')
                link = f'../{folder}/{course_info["file_name"]}.md'
                linked_prereqs.append(f'[{prereq}]({link})')
            else:
                linked_prereqs.append(prereq)
        
        if linked_prereqs:
            return '، '.join(linked_prereqs)
        else:
            return 'ندارد'
    
    def _create_markdown_table(self, data: List[List[str]]) -> str:
        """ایجاد جدول Markdown از داده‌های دو بعدی"""
        if not data:
            return ''
        
        headers = ['', '', '', '']
        separator = ['---', '---', '---', '---']
        
        table_lines = []
        table_lines.append('| ' + ' | '.join(headers) + ' |')
        table_lines.append('| ' + ' | '.join(separator) + ' |')
        
        for row in data:
            clean_row = [str(cell) if cell is not None else '' for cell in row]
            table_lines.append('| ' + ' | '.join(clean_row) + ' |')
        
        return '\n'.join(table_lines)
    
    def _clear_folders(self):
        """پاکسازی پوشه‌های خروجی"""
        for folder in list(self.subfolders.values()) + ['other']:
            dir_path = os.path.join(self.base_path, folder)
            if os.path.exists(dir_path):
                for file in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, file)
                    if os.path.isfile(file_path) and file != '_category_.json':
                        try:
                            os.remove(file_path)
                        except:
                            pass


def main():
    """تابع اصلی اجرای برنامه"""
    print("🔍 Starting DS Course Parser...")
    
    try:
        # 1. پارس کردن فایل DS-Chart.md
        parser = DSCourseParser('../input/DS-Chart.md')
        df = parser.parse_file()
        
        if df is None or len(df) == 0:
            print("❌ No data extracted!")
            return None
        
        # 2. تولید فایل‌های Markdown
        generator = DocusaurusMarkdownGenerator('./docs/curriculum/')
        generator.generate_files(df)
        
        print("\n✅ Process completed successfully!")
        
        # 3. نمایش نمونه
        if len(df) > 0:
            print("\n📋 Sample of extracted data (first 10):")
            sample_cols = ['fa_title', 'en_title', 'course_type', 'units', 'has_exercises']
            available_cols = [col for col in sample_cols if col in df.columns]
            print(df[available_cols].head(10).to_string())
        
        return df
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    df = main()