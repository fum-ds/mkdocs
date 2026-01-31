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
        
        # تقسیم محتوا به بخش‌های مختلف درس‌ها
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
            
            # استخراج اهداف - باید فقط متن تا بخش بعدی را بگیرد
            if 'اهداف درس:' in original_line:
                course_data['goals'] = self._extract_section_content(lines, i, 'اهداف درس:')
            
            # استخراج شایستگی‌ها
            if 'توانایی و شایستگی‌هایی که درس پرورش می‌دهد:' in original_line:
                course_data['competencies'] = self._extract_section_content(lines, i, 'توانایی و شایستگی‌هایی که درس پرورش می‌دهد:')
            
            # استخراج سرفصل
            if 'سرفصل درس:' in original_line:
                course_data['syllabus'] = self._extract_syllabus(lines, i)
            
            # استخراج منابع
            if 'منابع:' in original_line:
                course_data['references'] = self._extract_references(lines, i)
        
        # پردازش باقی‌مانده
        if table_lines:
            table_data = self._parse_table(table_lines)
            course_data.update(table_data)
        
        return course_data

    def _extract_section_content(self, lines: List[str], start_index: int, marker: str) -> str:
        """استخراج محتوای یک بخش تا شروع بخش بعدی"""
        content_lines = []
        marker_found = False
        
        # لیست مارکرهای بخش‌های بعدی
        next_section_markers = [
            'سرفصل درس:',
            'راهبردهای تدریس',
            'روش یاددهی-یادگیری',
            'روش یاددهی',
            'روش ارزیابی',
            'تجهیزات',
            'منابع:',
            '| # | # | # | # | # |',
            'عنوان درس به فارسی:'
        ]
        
        for i in range(start_index, len(lines)):
            current_line = lines[i]
            
            # اگر مارکر هدف را پیدا کردیم
            if marker in current_line and not marker_found:
                marker_found = True
                # متن بعد از مارکر را بگیر
                parts = current_line.split(marker, 1)
                if len(parts) > 1 and parts[1].strip():
                    content_lines.append(parts[1].strip())
                continue
            
            # اگر مارکر پیدا شده بود
            if marker_found:
                # بررسی کنیم آیا به بخش بعدی رسیده‌ایم
                is_next_section = False
                for next_marker in next_section_markers:
                    if next_marker in current_line:
                        is_next_section = True
                        break
                
                # اگر به بخش بعدی رسیدیم، متوقف شو
                if is_next_section:
                    break
                
                # اگر خط خالی یا جدول است، متوقف شو
                if not current_line.strip() or current_line.strip().startswith('|'):
                    # اما اگر در بخش سرفصل هستیم و جدول کوچک ارزیابی است، ادامه می‌دهیم
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
        return self._clean_text(combined_text)

    def _extract_syllabus(self, lines: List[str], start_index: int) -> List[str]:
        """استخراج سرفصل درس - هر آیتم در یک خط جدا"""
        syllabus_lines = []
        in_syllabus = False
        markers_to_stop = [
            'راهبردهای تدریس',
            'روش یاددهی-یادگیری',
            'روش یاددهی',
            'روش ارزیابی',
            'تجهیزات',
            'منابع:',
            '| # | # | # | # | # |',
            'عنوان درس به فارسی:'
        ]
        
        for i in range(start_index, len(lines)):
            current_line = lines[i]
            
            if 'سرفصل درس:' in current_line:
                in_syllabus = True
                # متن بعد از مارکر را بگیر
                parts = current_line.split('سرفصل درس:', 1)
                if len(parts) > 1 and parts[1].strip():
                    syllabus_lines.append(parts[1].strip())
                continue
            
            if in_syllabus:
                # بررسی کنیم آیا به بخش بعدی رسیده‌ایم
                should_stop = False
                for marker in markers_to_stop:
                    if marker in current_line:
                        should_stop = True
                        break
                
                if should_stop:
                    break
                
                # اگر خط خالی است، ادامه بده
                if not current_line.strip():
                    continue
                
                # اگر خط با | شروع می‌شود (جدول)، متوقف شو
                if current_line.strip().startswith('|'):
                    break
                
                # خط را اضافه کن
                clean_line = self._clean_text(current_line, keep_newlines=True)
                if clean_line:
                    syllabus_lines.append(clean_line)
        
        # پردازش سرفصل‌های استخراج شده
        processed_syllabus = []
        for line in syllabus_lines:
            if not line:
                continue
                
            # اگر خط حاوی ویرگول است، تقسیم کن
            if '،' in line or ',' in line:
                # ابتدا بر اساس ویرگول فارسی تقسیم کنیم
                if '،' in line:
                    items = [item.strip() for item in line.split('،') if item.strip()]
                else:
                    items = [item.strip() for item in line.split(',') if item.strip()]
                
                # فقط آیتم‌هایی که طول معقولی دارند را اضافه کن
                for item in items:
                    if len(item) > 3:  # حداقل 3 کاراکتر
                        processed_syllabus.append(item)
            else:
                if line.strip() and len(line.strip()) > 3:
                    processed_syllabus.append(line.strip())
        
        return processed_syllabus if processed_syllabus else []

    def _extract_references(self, lines: List[str], start_index: int) -> List[str]:
        """استخراج منابع - هر منبع در یک خط جدا"""
        ref_lines = []
        in_references = False
        next_course_markers = ['| # | # | # | # | # |', 'عنوان درس به فارسی:']
        
        for i in range(start_index, len(lines)):
            current_line = lines[i]
            
            if 'منابع:' in current_line:
                in_references = True
                # متن بعد از مارکر را بگیر
                parts = current_line.split('منابع:', 1)
                if len(parts) > 1 and parts[1].strip():
                    ref_lines.append(parts[1].strip())
                continue
            
            if in_references:
                # بررسی کنیم آیا به درس بعدی رسیده‌ایم
                should_stop = False
                for marker in next_course_markers:
                    if marker in current_line:
                        should_stop = True
                        break
                
                if should_stop:
                    break
                
                # اگر خط خالی است، ادامه بده
                if not current_line.strip():
                    continue
                
                # خط را اضافه کن
                clean_line = self._clean_text(current_line, keep_newlines=False, remove_br=True)
                if clean_line:
                    ref_lines.append(clean_line)
        
        return ref_lines

    def _parse_table(self, table_lines: List[str]) -> Dict:
        """پارس کردن جدول اطلاعات درس"""
        data = {}
        
        # روش ساده: خط به خط بررسی کنیم
        for line in table_lines:
            if not line.startswith('|'):
                continue
            
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            
            # استخراج اطلاعات از سلول‌ها
            for i, cell in enumerate(cells):
                # حذف تگ page و br از سلول
                cell_clean = self._clean_text(cell)
                
                if 'عنوان درس به فارسی:' in cell:
                    if i + 1 < len(cells):
                        fa_title = cells[i + 1]
                        data['fa_title'] = self._clean_text(fa_title)
                    break
                
                if 'عنوان درس به انگلیسی:' in cell:
                    if i + 1 < len(cells):
                        en_title = cells[i + 1]
                        data['en_title'] = self._clean_text(en_title)
                    break
                
                if 'دروس پیش‏نیاز:' in cell:
                    if i + 1 < len(cells):
                        prereq = cells[i + 1]
                        data['prerequisites'] = self._clean_text(prereq) if prereq else 'ندارد'
                    break
                
                if 'دروس هم‏نیاز:' in cell:
                    if i + 1 < len(cells):
                        coreq = cells[i + 1]
                        data['corequisites'] = self._clean_text(coreq) if coreq else 'ندارد'
                    break
                
                if 'تعداد واحد:' in cell:
                    if i + 1 < len(cells):
                        units = cells[i + 1]
                        # جدا کردن "حل تمرین دارد" از تعداد واحد
                        if 'حل تمرین دارد' in units:
                            units = units.replace('حل تمرین دارد', '').strip()
                            data['has_exercises'] = 'دارد'
                        elif 'حل تمرین ندارد' in units:
                            units = units.replace('حل تمرین ندارد', '').strip()
                            data['has_exercises'] = 'ندارد'
                        data['units'] = self._clean_text(units)
                    break
                
                if 'تعداد ساعت:' in cell:
                    if i + 1 < len(cells):
                        hours = cells[i + 1]
                        data['hours'] = self._clean_text(hours)
                    break
        
        # اگر هنوز حل تمرین مشخص نشده
        if 'has_exercises' not in data:
            # کل متن را بررسی کن
            full_text = ' '.join(table_lines)
            if 'حل تمرین دارد' in full_text:
                data['has_exercises'] = 'دارد'
            elif 'حل تمرین ندارد' in full_text:
                data['has_exercises'] = 'ندارد'
            else:
                data['has_exercises'] = ''
        
        # تشخیص نوع درس
        course_type = ''
        unit_type = 'نظری'
        
        # ابتدا به دنبال n می‌گردیم (مربع توپر)
        for line in table_lines:
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            
            for cell in cells:
                cell_clean = self._clean_text(cell)
                if 'n' in cell:  # مربع توپر
                    if 'پایه' in cell_clean:
                        course_type = 'پایه'
                    elif 'تخصصی الزامی' in cell_clean:
                        course_type = 'تخصصی الزامی'
                    elif 'تخصصی اختیاری' in cell_clean:
                        course_type = 'تخصصی اختیاری'
                    elif 'مهارتی' in cell_clean:
                        course_type = 'مهارتی'
                    
                    if 'نظری' in cell_clean:
                        unit_type = 'نظری'
                    elif 'عملی' in cell_clean:
                        unit_type = 'عملی'
                    elif 'نظری-عملی' in cell_clean:
                        unit_type = 'نظری-عملی'
        
        # اگر n پیدا نشد، به دنبال سلول‌های بدون £ می‌گردیم
        if not course_type:
            for line in table_lines:
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                
                for cell in cells:
                    cell_clean = self._clean_text(cell)
                    if '£' not in cell:  # مربع توخالی ندارد
                        if 'پایه' in cell_clean and 'n' not in cell:
                            course_type = 'پایه'
                        elif 'تخصصی الزامی' in cell_clean and 'n' not in cell:
                            course_type = 'تخصصی الزامی'
                        elif 'تخصصی اختیاری' in cell_clean and 'n' not in cell:
                            course_type = 'تخصصی اختیاری'
                        elif 'مهارتی' in cell_clean and 'n' not in cell:
                            course_type = 'مهارتی'
        
        data['course_type'] = course_type if course_type else ''
        data['unit_type'] = unit_type if unit_type else 'نظری'
        
        return data
    
    def _clean_text(self, text: str, keep_newlines: bool = False, remove_br: bool = True) -> str:
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
            if col not in ['syllabus', 'references']:
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
            
            # نمایش نمونه
            print(f"\n📋 Sample data (first 5):")
            sample_cols = ['fa_title', 'en_title', 'course_type', 'units', 'has_exercises']
            available_cols = [col for col in sample_cols if col in df.columns]
            print(df[available_cols].head(5).to_string())
        
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
            # اگر رشته است و حاوی ویرگول است، تقسیم کن
            syllabus_text = str(syllabus).strip()
            if '،' in syllabus_text:
                items = [item.strip() for item in syllabus_text.split('،') if item.strip()]
                for item in items:
                    lines.append(f"- {item}")
            elif ',' in syllabus_text:
                items = [item.strip() for item in syllabus_text.split(',') if item.strip()]
                for item in items:
                    lines.append(f"- {item}")
            else:
                lines.append(syllabus_text)
        else:
            lines.append('(سرفصل تعیین نشده است)')
        lines.append('')
        
        # منابع
        lines.append('### منابع')
        lines.append('')
        if isinstance(references, list) and references:
            for ref in references:
                if ref and str(ref).strip() and str(ref).strip() != 'nan':
                    # حذف تگ <br> اگر وجود دارد
                    clean_ref = str(ref).strip().replace('<br>', '').replace('<br/>', '')
                    lines.append(f"- {clean_ref}")
        elif references and str(references).strip() and str(references).strip() != 'nan':
            ref_text = str(references).strip()
            # حذف تگ <br>
            ref_text = ref_text.replace('<br>', '\n').replace('<br/>', '\n')
            # تقسیم بر اساس خطوط جدید
            ref_items = [item.strip() for item in ref_text.split('\n') if item.strip()]
            for item in ref_items:
                lines.append(f"- {item}")
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
        
        return df
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    df = main()