# ds_parser/parser.py
import re
import pandas as pd
from typing import List, Dict
from .models import Course
from .utils import clean_text, extract_section_content, split_course_sections

class DSCourseParser:
    """Parser برای فایل‌های برنامه درسی علوم داده"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.courses: List[Course] = []
        self.df = None
        
    def parse_file(self) -> pd.DataFrame:
        """پارس کردن فایل و استخراج اطلاعات درس‌ها"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        course_sections = split_course_sections(content)
        
        courses_data = []
        for section in course_sections:
            course_data = self._parse_course_section(section)
            if course_data and course_data.fa_title:
                courses_data.append(course_data)
        
        self._create_dataframe(courses_data)
        return self.df
    
    def _parse_course_section(self, section: str) -> Course:
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
            
            # استخراج بخش‌های مختلف
            course_data.update(self._extract_sections(lines, i))
        
        # پردازش باقی‌مانده
        if table_lines:
            table_data = self._parse_table(table_lines)
            course_data.update(table_data)
        
        return Course.from_dict(course_data)
    
    def _extract_sections(self, lines: List[str], index: int) -> Dict:
        """استخراج بخش‌های مختلف درس"""
        original_line = lines[index]
        sections = {}
        
        # استخراج اهداف
        if 'اهداف درس:' in original_line:
            sections['goals'] = extract_section_content(
                lines, index, 'اهداف درس:', 
                next_markers=['توانایی و شایستگی‌هایی که درس پرورش می‌دهد:', 'سرفصل درس:', 'راهبردهای تدریس']
            )
        
        # استخراج شایستگی‌ها
        if 'توانایی و شایستگی‌هایی که درس پرورش می‌دهد:' in original_line:
            sections['competencies'] = extract_section_content(
                lines, index, 'توانایی و شایستگی‌هایی که درس پرورش می‌دهد:', 
                next_markers=['سرفصل درس:', 'راهبردهای تدریس']
            )
        
        # استخراج سرفصل
        if 'سرفصل درس:' in original_line:
            sections['syllabus'] = self._extract_syllabus(lines, index)
        
        # استخراج راهبردهای تدریس
        if 'راهبردهای تدریس' in original_line:
            sections['teaching_strategies'] = extract_section_content(
                lines, index, 'راهبردهای تدریس و یادگیری متناسب با محتوا و هدف:', 
                next_markers=['روش یاددهی-یادگیری', 'روش یاددهی', 'روش ارزیابی']
            )
        
        # استخراج روش یاددهی-یادگیری
        if 'روش یاددهی-یادگیری:' in original_line:
            sections['teaching_methods'] = extract_section_content(
                lines, index, 'روش یاددهی-یادگیری:', 
                next_markers=['روش ارزیابی', 'تجهیزات']
            )
        elif 'روش یاددهی:' in original_line:
            sections['teaching_methods'] = extract_section_content(
                lines, index, 'روش یاددهی:', 
                next_markers=['روش ارزیابی', 'تجهیزات']
            )
        
        # استخراج روش ارزیابی
        if 'روش ارزیابی:' in original_line:
            sections['assessment_methods'] = extract_section_content(
                lines, index, 'روش ارزیابی:', 
                next_markers=['تجهیزات', 'منابع:']
            )
        
        # استخراج تجهیزات
        if 'تجهیزات' in original_line and 'تجهیزات و امکانات' not in original_line:
            sections['equipment'] = extract_section_content(
                lines, index, 'تجهیزات', 
                next_markers=['منابع:']
            )
        
        # استخراج منابع
        if 'منابع:' in original_line:
            sections['references'] = self._extract_references(lines, index)
        
        return sections
    
    def _extract_syllabus(self, lines: List[str], start_index: int) -> str:
        """استخراج سرفصل درس"""
        syllabus_lines = []
        in_syllabus = False
        markers_to_stop = ['راهبردهای تدریس', 'روش یاددهی-یادگیری', 'روش یاددهی', 
                          'روش ارزیابی', 'تجهیزات', 'منابع:', '| # | # | # | # | # |']
        
        for i in range(start_index, len(lines)):
            current_line = lines[i]
            
            if 'سرفصل درس:' in current_line:
                in_syllabus = True
                parts = current_line.split('سرفصل درس:', 1)
                if len(parts) > 1 and parts[1].strip():
                    syllabus_lines.append(parts[1].strip())
                continue
            
            if in_syllabus:
                should_stop = any(marker in current_line for marker in markers_to_stop)
                if should_stop:
                    break
                
                if not current_line.strip() or current_line.strip().startswith('|'):
                    continue
                
                clean_line = clean_text(current_line, keep_newlines=True)
                if clean_line:
                    syllabus_lines.append(clean_line)
        
        combined_syllabus = ' '.join(syllabus_lines).strip()
        return re.sub(r'\s+', ' ', combined_syllabus)
    
    def _extract_references(self, lines: List[str], start_index: int) -> List[str]:
        """استخراج منابع"""
        ref_lines = []
        in_references = False
        
        for i in range(start_index, len(lines)):
            current_line = lines[i]
            
            if 'منابع:' in current_line:
                in_references = True
                parts = current_line.split('منابع:', 1)
                if len(parts) > 1 and parts[1].strip():
                    ref_lines.append(parts[1].strip())
                continue
            
            if in_references:
                if '| # | # | # | # | # |' in current_line or 'عنوان درس به فارسی:' in current_line:
                    break
                
                if not current_line.strip():
                    continue
                
                clean_line = clean_text(current_line, keep_newlines=False, remove_br=True)
                if clean_line:
                    ref_lines.append(clean_line)
        
        return ref_lines
    
    def _parse_table(self, table_lines: List[str]) -> Dict:
        """پارس کردن جدول اطلاعات درس"""
        data = {}
        
        for line in table_lines:
            if not line.startswith('|'):
                continue
            
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            
            for i, cell in enumerate(cells):
                cell_clean = clean_text(cell)
                
                if 'عنوان درس به فارسی:' in cell and i + 1 < len(cells):
                    data['fa_title'] = clean_text(cells[i + 1])
                    break
                
                if 'عنوان درس به انگلیسی:' in cell and i + 1 < len(cells):
                    data['en_title'] = clean_text(cells[i + 1])
                    break
                
                if 'دروس پیش‏نیاز:' in cell and i + 1 < len(cells):
                    prereq = cells[i + 1]
                    data['prerequisites'] = clean_text(prereq) if prereq else 'ندارد'
                    break
                
                if 'دروس هم‏نیاز:' in cell and i + 1 < len(cells):
                    coreq = cells[i + 1]
                    data['corequisites'] = clean_text(coreq) if coreq else 'ندارد'
                    break
                
                if 'تعداد واحد:' in cell and i + 1 < len(cells):
                    units = cells[i + 1]
                    if 'حل تمرین دارد' in units:
                        units = units.replace('حل تمرین دارد', '').strip()
                        data['has_exercises'] = 'دارد'
                    elif 'حل تمرین ندارد' in units:
                        units = units.replace('حل تمرین ندارد', '').strip()
                        data['has_exercises'] = 'ندارد'
                    data['units'] = clean_text(units)
                    break
                
                if 'تعداد ساعت:' in cell and i + 1 < len(cells):
                    data['hours'] = clean_text(cells[i + 1])
                    break
        
        # تشخیص حل تمرین
        if 'has_exercises' not in data:
            full_text = ' '.join(table_lines)
            if 'حل تمرین دارد' in full_text:
                data['has_exercises'] = 'دارد'
            elif 'حل تمرین ندارد' in full_text:
                data['has_exercises'] = 'ندارد'
            else:
                data['has_exercises'] = ''
        
        # تشخیص نوع درس
        data.update(self._detect_course_type(table_lines))
        
        return data
    
    def _detect_course_type(self, table_lines: List[str]) -> Dict:
        """تشخیص نوع درس و نوع واحد"""
        course_type = ''
        unit_type = 'نظری'
        
        for line in table_lines:
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            
            for cell in cells:
                cell_clean = clean_text(cell)
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
        
        # اگر n پیدا نشد
        if not course_type:
            for line in table_lines:
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                
                for cell in cells:
                    cell_clean = clean_text(cell)
                    if '£' not in cell:  # مربع توخالی ندارد
                        if 'پایه' in cell_clean and 'n' not in cell:
                            course_type = 'پایه'
                        elif 'تخصصی الزامی' in cell_clean and 'n' not in cell:
                            course_type = 'تخصصی الزامی'
                        elif 'تخصصی اختیاری' in cell_clean and 'n' not in cell:
                            course_type = 'تخصصی اختیاری'
                        elif 'مهارتی' in cell_clean and 'n' not in cell:
                            course_type = 'مهارتی'
        
        return {
            'course_type': course_type if course_type else '',
            'unit_type': unit_type if unit_type else 'نظری'
        }
    
    def _create_dataframe(self, courses_data: List[Course]):
        """ایجاد DataFrame از داده‌های استخراج شده"""
        if not courses_data:
            print("❌ No course data extracted!")
            self.df = pd.DataFrame()
            return self.df
        
        # تبدیل Course objects به dictionaries
        courses_dicts = [course.to_dict() for course in courses_data]
        
        df = pd.DataFrame(courses_dicts)
        df = df.fillna('')
        
        # ایجاد نام فایل
        from .utils import create_filename
        df['en_file_name'] = df['en_title'].apply(create_filename)
        df['c_cat'] = df['course_type']
        
        self.df = df
        
        # نمایش آمار
        print(f"\n📈 Extraction Statistics:")
        print(f"Total valid courses: {len(df)}")
        
        if len(df) > 0:
            print(f"\n📊 Course types distribution:")
            print(df['course_type'].value_counts())
            
            print(f"\n📊 Has exercises distribution:")
            print(df['has_exercises'].value_counts())
        
        return self.df