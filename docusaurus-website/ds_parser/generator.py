# ds_parser/generator.py
import os
import pandas as pd
from typing import List, Dict
from .models import Course

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
        self.course_mapping: Dict[str, Dict] = {}
    
    def generate_files(self, df: pd.DataFrame):
        """تولید فایل‌های Markdown برای همه درس‌ها"""
        if df is None or len(df) == 0:
            print("❌ No data to generate files!")
            return
        
        print(f"\n🎯 Generating files for {len(df)} courses...")
        
        df = df.fillna('')
        self._create_course_mapping(df)
        
        # تعیین موقعیت درس‌ها
        df['position'] = self._calculate_positions(df)
        
        self._clear_folders()
        
        # ایجاد فایل برای هر درس
        generated_count = 0
        for _, row in df.iterrows():
            if self._generate_course_file(row):
                generated_count += 1
        
        self._print_summary(generated_count)
    
    def _create_course_mapping(self, df: pd.DataFrame):
        """ایجاد نگاشت عنوان فارسی به نام فایل"""
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
    
    def _calculate_positions(self, df: pd.DataFrame) -> List[int]:
        """محاسبه موقعیت درس‌ها در سایدبار"""
        positions = []
        position_counter = {}
        
        for _, row in df.iterrows():
            course_type = str(row['course_type']).strip()
            if not course_type or course_type == 'nan':
                course_type = 'other'
            
            if course_type not in position_counter:
                position_counter[course_type] = 1
            else:
                position_counter[course_type] += 1
            
            positions.append(position_counter[course_type])
        
        return positions
    
    def _generate_course_file(self, row) -> bool:
        """ایجاد فایل Markdown برای یک درس"""
        try:
            fa_title = str(row['fa_title']).strip()
            en_file_name = str(row['en_file_name']).strip()
            course_type = str(row['course_type']).strip()
            
            if not fa_title or fa_title == 'nan' or not en_file_name or en_file_name == 'nan':
                return False
            
            folder = self.subfolders.get(course_type, 'other')
            file_path = os.path.join(self.base_path, folder, f"{en_file_name}.md")
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            content = self._create_file_content(row, folder)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating file for {row.get('fa_title', 'Unknown')}: {str(e)}")
            return False
    
    def _create_file_content(self, row, folder: str) -> str:
        """ایجاد محتوای فایل Markdown"""
        lines = []
        
        # Frontmatter
        lines.append('---')
        lines.append(f"sidebar_position: {int(row['position'])}")
        lines.append('---')
        lines.append('')
        
        # عنوان‌ها
        lines.append(f"# {str(row['fa_title']).strip()}")
        lines.append('')
        
        en_title = str(row['en_title']).strip()
        if en_title and en_title != 'nan':
            lines.append(f"## {en_title}")
            lines.append('')
        
        lines.append('---')
        lines.append('')
        
        # اطلاعات درس
        lines.append('### اطلاعات درس')
        lines.append('')
        lines.append(self._create_info_table(row))
        lines.append('')
        
        # اضافه کردن بخش‌های مختلف
        sections = [
            ('goals', 'اهداف درس'),
            ('competencies', 'توانایی‌ها و شایستگی‌ها'),
            ('syllabus', 'سرفصل درس'),
            ('teaching_strategies', 'راهبردهای تدریس و یادگیری'),
            ('teaching_methods', 'روش یاددهی-یادگیری'),
            ('assessment_methods', 'روش ارزیابی'),
            ('equipment', 'تجهیزات و امکانات موردنیاز')
        ]
        
        for field_name, title in sections:
            if field_name in row and str(row[field_name]).strip() and str(row[field_name]).strip() != 'nan':
                content = str(row[field_name]).strip()
                if content and content != 'ندارد':
                    lines.append(f"### {title}")
                    lines.append('')
                    lines.append(content)
                    lines.append('')
        
        # منابع
        lines.append('### منابع')
        lines.append('')
        lines.append(self._format_references(row))
        
        return '\n'.join(lines)
    
    def _create_info_table(self, row) -> str:
        """ایجاد جدول اطلاعات درس"""
        fa_title = str(row['fa_title']).strip()
        prerequisites = self._format_prerequisites(str(row['prerequisites']).strip(), fa_title)
        corequisites = self._format_prerequisites(str(row['corequisites']).strip(), fa_title)
        course_type = str(row['course_type']).strip()
        unit_type = str(row['unit_type']).strip()
        units = str(row['units']).strip()
        hours = str(row['hours']).strip()
        has_exercises = str(row['has_exercises']).strip()
        
        info_table = [
            ['نام درس:', fa_title, 'مقطع:', 'کارشناسی'],
            ['پیش‌نیاز:', prerequisites, 'گروه درس:', course_type],
            ['هم‌نیاز:', corequisites, 'نوع درس:', unit_type],
            ['تعداد واحد:', units, 'تعداد ساعت:', hours],
            ['حل تمرین:', has_exercises, '', '']
        ]
        
        return self._create_markdown_table(info_table)
    
    def _format_prerequisites(self, prereq_str: str, current_course: str = '') -> str:
        """فرمت‌بندی پیش‌نیازها با لینک"""
        if not prereq_str or prereq_str in ['ندارد', 'nan']:
            return 'ندارد'
        
        prereq_str = str(prereq_str)
        
        # تقسیم پیش‌نیازها
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
        
        return '، '.join(linked_prereqs) if linked_prereqs else 'ندارد'
    
    def _format_references(self, row) -> str:
        """فرمت‌بندی منابع"""
        references = row['references']
        lines = []
        
        if isinstance(references, list) and references:
            for ref in references:
                if ref and str(ref).strip() and str(ref).strip() != 'nan':
                    clean_ref = str(ref).strip().replace('<br>', '').replace('<br/>', '')
                    lines.append(f"- {clean_ref}")
        elif references and str(references).strip() and str(references).strip() != 'nan':
            ref_text = str(references).strip()
            ref_text = ref_text.replace('<br>', '\n').replace('<br/>', '\n')
            ref_items = [item.strip() for item in ref_text.split('\n') if item.strip()]
            for item in ref_items:
                lines.append(f"- {item}")
        else:
            lines.append('(منابع تعیین نشده است)')
        
        return '\n'.join(lines) if lines else '(منابع تعیین نشده است)'
    
    def _create_markdown_table(self, data: List[List[str]]) -> str:
        """ایجاد جدول Markdown"""
        if not data:
            return ''
        
        table_lines = [
            '|  |  |  |  |',
            '| --- | --- | --- | --- |'
        ]
        
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
    
    def _print_summary(self, generated_count: int):
        """چاپ خلاصه تولید فایل‌ها"""
        print(f"\n✅ Successfully generated {generated_count} files")
        print(f"\n📁 Files generated in folders:")
        
        for course_type, folder in self.subfolders.items():
            folder_path = os.path.join(self.base_path, folder)
            if os.path.exists(folder_path):
                files = [f for f in os.listdir(folder_path) if f.endswith('.md')]
                if files:
                    print(f"  📂 {folder}/: {len(files)} files")
        
        other_path = os.path.join(self.base_path, 'other')
        if os.path.exists(other_path):
            files = [f for f in os.listdir(other_path) if f.endswith('.md')]
            if files:
                print(f"  📂 other/: {len(files)} files (no type detected)")