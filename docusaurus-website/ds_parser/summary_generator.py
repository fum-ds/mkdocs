# ds_parser/summary_generator.py
import os
import pandas as pd
from typing import Dict, List, Tuple
from pathlib import Path
import unicodedata
from .utils import persian_sort_key  

class SummaryTableGenerator:
    """تولید کننده جداول خلاصه درس‌ها بر اساس نوع"""
    
    def __init__(self, base_path: str = './docs/curriculum/'):
        self.base_path = base_path
        self.subfolders = {
            'پایه': ('base', 'دروس پایه'),
            'تخصصی الزامی': ('mandatory', 'دروس الزامی'),
            'مهارتی': ('skill', 'دروس مهارتی'),
            'تخصصی اختیاری': ('elective', 'دروس اختیاری')
        }
        # اضافه کردن نگاشت عنوان فارسی به اطلاعات درس
        self.course_mapping: Dict[str, Dict] = {}
    
    def generate_summary_tables(self, df: pd.DataFrame, output_file: str = './docs/summary-tables.md'):
        """تولید فایل Markdown حاوی جداول خلاصه"""
        print(f"\n📊 Generating summary tables...")
        
        # اطمینان از string بودن مقادیر
        df = df.fillna('')
        
        # ایجاد نگاشت عنوان فارسی به اطلاعات درس
        self._create_course_mapping(df)
        
        # ایجاد محتوای جداول
        tables_content = []
        tables_content.append('# جداول دروس پایه، تخصصی و اختیاری\n')
        
        total_units_all = 0
        
        # ایجاد جدول برای هر نوع درس
        for course_type, (folder, title) in self.subfolders.items():
            type_courses = df[df['course_type'] == course_type].copy()
            
            if len(type_courses) > 0:
                table_content, total_units = self._create_type_table(
                    type_courses, course_type, folder, title, df
                )
                tables_content.append(table_content)
                total_units_all += total_units
        
        # اضافه کردن جدول دروس بدون نوع (other)
        other_courses = df[df['course_type'] == ''].copy()
        if len(other_courses) > 0:
            table_content, total_units = self._create_type_table(
                other_courses, '', 'other', 'دروس بدون نوع', df
            )
            tables_content.append(table_content)
            total_units_all += total_units
        
        # اضافه کردن خلاصه کلی
        tables_content.append(self._create_overall_summary(total_units_all))
        
        # ایجاد پوشه خروجی اگر وجود ندارد
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # نوشتن در فایل
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(tables_content))
        
        print(f"✅ Summary tables generated: {output_file}")
        
        return output_file
    
    def _create_course_mapping(self, df: pd.DataFrame):
        """ایجاد نگاشت عنوان فارسی به اطلاعات درس"""
        for _, row in df.iterrows():
            fa_title = str(row['fa_title']).strip()
            en_file_name = str(row['en_file_name']).strip()
            course_type = str(row['course_type']).strip()
            
            if fa_title and fa_title != 'nan' and en_file_name:
                self.course_mapping[fa_title] = {
                    'file_name': en_file_name,
                    'course_type': course_type
                }
        
        print(f"📚 Created {len(self.course_mapping)} course mappings for summary tables")
    
    def _create_type_table(self, courses_df: pd.DataFrame, course_type: str, 
                          folder: str, title: str, all_courses_df: pd.DataFrame) -> Tuple[str, int]:
        """ایجاد جدول برای یک نوع درس خاص با مرتب‌سازی الفبایی فارسی"""
        
        # ✅ تغییر: مرتب‌سازی بر اساس حروف الفبای فارسی
        courses_df = self._sort_by_persian_alphabet(courses_df)
        
        # ایجاد ردیف‌های جدول
        table_rows = []
        total_units = 0
        
        # شمارنده موقعیت برای نمایش ترتیب
        position_counter = 1
        
        for _, row in courses_df.iterrows():
            fa_title = str(row['fa_title']).strip()
            en_file_name = str(row['en_file_name']).strip()
            prerequisites = str(row['prerequisites']).strip()
            units = str(row['units']).strip()
            
            if not fa_title or fa_title == 'nan':
                continue
            
            # ایجاد لینک به صفحه درس
            if en_file_name and en_file_name != 'nan':
                # ✅ لینک صحیح (مطلق از روت سایت)
                link = f'/docs/curriculum/{folder}/{en_file_name}.md'
                title_cell = f'[{fa_title}]({link})'
            else:
                title_cell = fa_title
            
            # فرمت‌بندی پیش‌نیازها با لینک
            prereq_formatted = self._format_prerequisites_for_table(
                prerequisites, all_courses_df, folder
            )
            
            # ✅ اضافه کردن شماره ردیف (اختیاری)
            # title_cell = f"{position_counter}. {title_cell}"
            
            # اضافه کردن ردیف
            table_rows.append(f'|{title_cell}|{prereq_formatted}|{units}|')
            
            # جمع‌آوری تعداد واحدها
            try:
                if units and units != 'nan':
                    total_units += int(float(units))
            except (ValueError, TypeError):
                pass
            
            position_counter += 1
        
        # اگر هیچ درسی نداریم، جدول خالی برمی‌گردانیم
        if not table_rows:
            return f'## {title}\n\n*(هیچ درسی یافت نشد)*\n', 0
        
        # ایجاد محتوای جدول
        table_content = [
            f'## {title}\n',
            '| نام درس | پیش‌نیاز | تعداد واحد |',
            '| ------- | -------- | ---------- |',
            *table_rows,
            f'| **مجموع تعداد واحد** |**{title}**|**{total_units}**|'
        ]
        
        # نمایش ترتیب مرتب‌سازی شده
        print(f"  📋 {title}: {len(courses_df)} درس (مرتب شده بر اساس الفبای فارسی)")
        
        return '\n'.join(table_content), total_units
    
    def _sort_by_persian_alphabet(self, df: pd.DataFrame) -> pd.DataFrame:
        """مرتب‌سازی DataFrame بر اساس حروف الفبای فارسی"""
        if len(df) == 0:
            return df
        
        # کپی DataFrame
        df_sorted = df.copy()
        
        # ایجاد ستون برای کلید مرتب‌سازی
        df_sorted['sort_key'] = df_sorted['fa_title'].apply(persian_sort_key)
        
        # مرتب‌سازی بر اساس کلید
        df_sorted = df_sorted.sort_values('sort_key')
        
        # حذف ستون موقت
        df_sorted = df_sorted.drop('sort_key', axis=1)
        
        return df_sorted


    def _format_prerequisites_for_table(self, prereq_str: str, 
                                      all_courses_df: pd.DataFrame, 
                                      current_folder: str) -> str:
        """فرمت‌بندی پیش‌نیازها برای جدول خلاصه (با جستجو در تمام دروس)"""
        if not prereq_str or prereq_str in ['ندارد', 'nan']:
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
        
        # ایجاد لینک برای هر پیش‌نیاز
        linked_prereqs = []
        for prereq in prereqs:
            # جستجوی پیش‌نیاز در بین تمام دروس
            found = False
            
            # روش ۱: جستجو در course_mapping (سریع‌تر)
            if prereq in self.course_mapping:
                course_info = self.course_mapping[prereq]
                course_type = course_info['course_type']
                
                # تعیین پوشه بر اساس نوع درس
                if course_type in self.subfolders:
                    folder = self.subfolders[course_type][0]
                else:
                    folder = 'other'
                
                file_name = course_info['file_name']
                # ✅ لینک صحیح
                link = f'/docs/curriculum/{folder}/{file_name}.md'
                linked_prereqs.append(f'[{prereq}]({link})')
                found = True
            
            # روش ۲: جستجو در all_courses_df (برای اطمینان)
            if not found:
                for _, course_row in all_courses_df.iterrows():
                    if str(course_row['fa_title']).strip() == prereq:
                        en_file_name = str(course_row['en_file_name']).strip()
                        course_type = str(course_row['course_type']).strip()
                        
                        if en_file_name and en_file_name != 'nan':
                            # تعیین پوشه بر اساس نوع درس
                            if course_type in self.subfolders:
                                folder = self.subfolders[course_type][0]
                            else:
                                folder = 'other'
                            
                            # ✅ لینک صحیح
                            link = f'/docs/curriculum/{folder}/{en_file_name}.md'
                            linked_prereqs.append(f'[{prereq}]({link})')
                            found = True
                            break
            
            # اگر پیدا نشد، بدون لینک نمایش داده شود
            if not found:
                linked_prereqs.append(prereq)
        
        return '، '.join(linked_prereqs) if linked_prereqs else 'ندارد'
    
    def _create_overall_summary(self, total_units: int) -> str:
        """ایجاد خلاصه کلی"""
        return f"""## خلاصه کلی

| نوع درس | تعداد واحد |
| ------- | ---------- |
| **مجموع کل واحدها** | **{total_units}** |

> **نکته**: این تعداد واحد شامل دروس پایه، الزامی، اختیاری و مهارتی می‌شود.
"""
    
    def generate_detailed_summary(self, df: pd.DataFrame, output_file: str = './docs/detailed-summary.md'):
        """تولید خلاصه دقیق با جزئیات بیشتر"""
        print(f"\n📈 Generating detailed summary...")
        
        df = df.fillna('')
        
        # ایجاد نگاشت
        self._create_course_mapping(df)
        
        sections = []
        sections.append('# خلاصه دقیق برنامه درسی\n')
        
        # آمار کلی
        total_courses = len(df)
        sections.append(self._create_overall_stats(df, total_courses))
        
        # جداول تفکیک شده
        for course_type, (folder, title) in self.subfolders.items():
            type_courses = df[df['course_type'] == course_type].copy()
            
            if len(type_courses) > 0:
                # ✅ مرتب‌سازی الفبایی برای detailed tables هم
                type_courses_sorted = self._sort_by_persian_alphabet(type_courses)
                sections.append(self._create_detailed_type_table(
                    type_courses_sorted, title, folder, df
                ))
        
        # دروس بدون نوع
        other_courses = df[df['course_type'] == ''].copy()
        if len(other_courses) > 0:
            other_courses_sorted = self._sort_by_persian_alphabet(other_courses)
            sections.append(self._create_detailed_type_table(
                other_courses_sorted, 'دروس بدون نوع', 'other', df
            ))
        
        # ایجاد فایل
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(sections))
        
        print(f"✅ Detailed summary generated: {output_file}")
        
        return output_file
    
    def _create_overall_stats(self, df: pd.DataFrame, total_courses: int) -> str:
        """ایجاد آمار کلی"""
        stats_lines = [
            '## آمار کلی\n',
            '| معیار | مقدار |',
            '| ----- | ----- |',
            f'| تعداد کل درس‌ها | {total_courses} |'
        ]
        
        # توزیع انواع درس
        if 'course_type' in df.columns:
            type_counts = df['course_type'].value_counts()
            for course_type, count in type_counts.items():
                if course_type:
                    persian_type = self._get_persian_type_name(course_type)
                    stats_lines.append(f'| تعداد {persian_type} | {count} |')
        
        # توزیع تعداد واحدها
        if 'units' in df.columns:
            try:
                total_units = df['units'].apply(lambda x: int(float(x)) if str(x).isdigit() else 0).sum()
                stats_lines.append(f'| مجموع واحدها | {total_units} |')
                
                # میانگین واحدها
                avg_units = total_units / total_courses if total_courses > 0 else 0
                stats_lines.append(f'| میانگین واحد هر درس | {avg_units:.1f} |')
            except:
                pass
        
        # توزیع حل تمرین
        if 'has_exercises' in df.columns:
            has_ex = (df['has_exercises'] == 'دارد').sum()
            no_ex = (df['has_exercises'] == 'ندارد').sum()
            stats_lines.append(f'| درس‌های با حل تمرین | {has_ex} |')
            stats_lines.append(f'| درس‌های بدون حل تمرین | {no_ex} |')
        
        return '\n'.join(stats_lines)
    
    def _create_detailed_type_table(self, courses_df: pd.DataFrame, title: str, 
                                   folder: str, all_courses_df: pd.DataFrame) -> str:
        """ایجاد جدول دقیق برای یک نوع درس (مرتب شده الفبایی)"""
        # ✅ مرتب‌سازی از قبل انجام شده
        
        table_rows = []
        total_units = 0
        
        position_counter = 1
        
        for _, row in courses_df.iterrows():
            fa_title = str(row['fa_title']).strip()
            en_file_name = str(row['en_file_name']).strip()
            prerequisites = str(row['prerequisites']).strip()
            units = str(row['units']).strip()
            hours = str(row['hours']).strip() if 'hours' in row else ''
            has_exercises = str(row['has_exercises']).strip() if 'has_exercises' in row else ''
            
            if not fa_title or fa_title == 'nan':
                continue
            
            # ایجاد لینک
            if en_file_name and en_file_name != 'nan':
                # ✅ لینک صحیح
                link = f'/docs/curriculum/{folder}/{en_file_name}.md'
                title_cell = f'[{fa_title}]({link})'
            else:
                title_cell = fa_title
            
            # ✅ اضافه کردن شماره ردیف (اختیاری)
            # title_cell = f"{position_counter}. {title_cell}"
            
            # فرمت‌بندی پیش‌نیازها
            prereq_formatted = self._format_prerequisites_for_table(
                prerequisites, all_courses_df, folder
            )
            
            # اطلاعات اضافی (بدون استفاده از HTML)
            additional_info = []
            if units and units != 'nan':
                additional_info.append(f'{units} واحد')
                try:
                    total_units += int(float(units))
                except:
                    pass
            
            if hours and hours != 'nan':
                additional_info.append(f'{hours} ساعت')
            
            if has_exercises and has_exercises != 'nan':
                additional_info.append(f'حل تمرین: {has_exercises}')
            
            # استفاده از خط جدید Markdown به جای <br>
            info_cell = '  \n'.join(additional_info) if additional_info else '-'
            
            # اضافه کردن ردیف
            table_rows.append(f'|{title_cell}|{prereq_formatted}|{info_cell}|')
            
            position_counter += 1
        
        if not table_rows:
            return f'## {title}\n\n*(هیچ درسی یافت نشد)*\n'
        
        table_content = [
            f'## {title}\n',
            '| نام درس | پیش‌نیاز | اطلاعات |',
            '| ------- | -------- | -------- |',
            *table_rows,
            f'| **مجموع** | **{len(courses_df)} درس** | **{total_units} واحد** |'
        ]
        
        return '\n'.join(table_content)
    
    def _get_persian_type_name(self, course_type: str) -> str:
        """تبدیل نوع درس به نام فارسی"""
        type_mapping = {
            'پایه': 'دروس پایه',
            'تخصصی الزامی': 'دروس الزامی',
            'تخصصی اختیاری': 'دروس اختیاری',
            'مهارتی': 'دروس مهارتی'
        }
        return type_mapping.get(course_type, course_type)
    
    def _print_sorting_sample(self, df: pd.DataFrame, course_type: str, title: str):
        """نمایش نمونه‌ای از مرتب‌سازی الفبایی"""
        type_courses = df[df['course_type'] == course_type].copy()
        if len(type_courses) > 0:
            sorted_courses = self._sort_by_persian_alphabet(type_courses)
            print(f"\n🔤 {title} - مرتب‌سازی الفبایی:")
            for i, (_, row) in enumerate(sorted_courses.head(5).iterrows(), 1):
                print(f"  {i}. {row['fa_title']}")
            if len(sorted_courses) > 5:
                print(f"  ... و {len(sorted_courses) - 5} درس دیگر")