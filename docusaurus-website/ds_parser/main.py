# ds_parser/main.py
import sys
import os
import pandas as pd
import urllib.parse
from pathlib import Path

# اضافه کردن مسیر ماژول به sys.path
sys.path.insert(0, str(Path(__file__).parent))

from .parser import DSCourseParser
from .generator import DocusaurusMarkdownGenerator
from .summary_generator import SummaryTableGenerator

def _create_safe_anchor(title: str) -> str:
    """ایجاد Anchor ایمن برای لینک‌های داخلی"""
    # تبدیل به حروف کوچک
    anchor = title.lower()
    # حذف علائم نگارشی
    anchor = anchor.replace(':', '').replace('،', '').replace(',', '')
    # جایگزینی فاصله با خط تیره
    anchor = anchor.replace(' ', '-')
    # حذف کاراکترهای غیر ASCII
    anchor = ''.join(c for c in anchor if c.isalnum() or c == '-')
    # حذف خط تیره‌های تکراری
    while '--' in anchor:
        anchor = anchor.replace('--', '-')
    # حذف خط تیره از ابتدا و انتها
    anchor = anchor.strip('-')
    
    return anchor

def _generate_index_file(df: pd.DataFrame, summary_file: str, detailed_file: str) -> None:
    """تولید فایل index.md برای سازماندهی بهتر"""
    index_content = """# برنامه درسی علوم داده

این بخش شامل اطلاعات کامل درباره برنامه درسی رشته علوم داده می‌باشد.

## بخش‌های مختلف

1. **[فهرست درس‌ها](category/برنامه-درسی)**: اطلاعات کامل هر درس به صورت جداگانه
2. **[جداول خلاصه](summary-tables)**: جداول طبقه‌بندی شده درس‌ها با لینک
3. **[خلاصه آماری](detailed-summary)**: آمار و اطلاعات دقیق برنامه درسی

## دسترسی سریع

"""
    
    # ایجاد Anchorهای ایمن برای لینک‌های داخلی
    section_titles = [
        ('دروس پایه', 'base-courses'),
        ('دروس الزامی', 'mandatory-courses'),
        ('دروس اختیاری', 'elective-courses'),
        ('دروس مهارتی', 'skill-courses')
    ]
    
    for persian_title, english_anchor in section_titles:
        index_content += f"- [{persian_title}](summary-tables#{english_anchor})\n"
    
    index_content += "\n## آمار کلی\n\n"
    
    # اضافه کردن آمار کلی
    total_courses = len(df)
    type_counts = df['course_type'].value_counts()
    
    index_content += f"- تعداد کل درس‌ها: **{total_courses}**\n"
    
    # محاسبه انواع درس
    type_mapping = {
        'پایه': ('دروس پایه', 'base'),
        'تخصصی الزامی': ('دروس الزامی', 'mandatory'),
        'تخصصی اختیاری': ('دروس اختیاری', 'elective'),
        'مهارتی': ('دروس مهارتی', 'skill')
    }
    
    for course_type, count in type_counts.items():
        if course_type in type_mapping:
            persian_name, _ = type_mapping[course_type]
            index_content += f"- تعداد {persian_name}: **{count}**\n"
    
    # درس‌های بدون نوع
    if '' in type_counts:
        index_content += f"- تعداد دروس بدون نوع: **{type_counts['']}**\n"
    
    # محاسبه مجموع واحدها
    try:
        total_units = df['units'].apply(lambda x: int(float(x)) if str(x).isdigit() else 0).sum()
        index_content += f"- مجموع واحدها: **{total_units}**\n"
        
        # محاسبه میانگین واحدها
        avg_units = total_units / total_courses if total_courses > 0 else 0
        index_content += f"- میانگین واحد هر درس: **{avg_units:.1f}**\n"
    except:
        pass
    
    # محاسبه درس‌های با/بدون حل تمرین
    if 'has_exercises' in df.columns:
        has_ex = (df['has_exercises'] == 'دارد').sum()
        no_ex = (df['has_exercises'] == 'ندارد').sum()
        unknown_ex = total_courses - has_ex - no_ex
        
        index_content += f"- درس‌های با حل تمرین: **{has_ex}**\n"
        index_content += f"- درس‌های بدون حل تمرین: **{no_ex}**\n"
        if unknown_ex > 0:
            index_content += f"- درس‌های با وضعیت نامشخص: **{unknown_ex}**\n"
    
    # اضافه کردن لینک‌های بیشتر
    index_content += """
## اطلاعات بیشتر

برای مشاهده جزئیات کامل هر درس، بر روی نام درس در [جداول خلاصه](summary-tables) کلیک کنید.

## ساختار

- **برنامه درسی**: فایل‌های جداگانه هر درس (دسته‌بندی شده)
- **جداول خلاصه**: جداول طبقه‌بندی شده با لینک
- **خلاصه آماری**: آمار و تحلیل‌های دقیق

---
*آخرین به‌روزرسانی: به صورت خودکار تولید شده*
"""
    
    # ایجاد فایل
    os.makedirs('./docs', exist_ok=True)
    with open('./docs/index.md', 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    print("✅ Index file generated: ./docs/index.md")

def _update_summary_tables_anchors(file_path: str) -> None:
    """به‌روزرسانی Anchorها در فایل summary-tables.md"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # جایگزینی Anchorهای فارسی با انگلیسی
        anchor_mapping = {
            '## دروس پایه': '## دروس پایه {#base-courses}',
            '## دروس الزامی': '## دروس الزامی {#mandatory-courses}',
            '## دروس اختیاری': '## دروس اختیاری {#elective-courses}',
            '## دروس مهارتی': '## دروس مهارتی {#skill-courses}',
            '## دروس بدون نوع': '## دروس بدون نوع {#other-courses}'
        }
        
        for old, new in anchor_mapping.items():
            content = content.replace(old, new)
        
        # نوشتن فایل به‌روزرسانی شده
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Updated anchors in: {file_path}")
        
    except Exception as e:
        print(f"⚠️  Could not update anchors: {str(e)}")

def _simplify_detailed_summary(file_path: str) -> None:
    """ساده‌سازی فایل detailed-summary به فقط آمار کلی"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # فقط بخش آمار کلی را نگه داریم
        lines = content.split('\n')
        simplified_lines = []
        in_stats_section = False
        stats_section_end = False
        
        for line in lines:
            if line.strip() == '## آمار کلی':
                in_stats_section = True
                simplified_lines.append(line)
            elif in_stats_section and line.strip().startswith('## ') and line.strip() != '## آمار کلی':
                stats_section_end = True
                break
            elif in_stats_section and not stats_section_end:
                simplified_lines.append(line)
            elif not in_stats_section and line.strip() == '# خلاصه دقیق برنامه درسی':
                simplified_lines.append('# خلاصه آماری برنامه درسی')
            elif not in_stats_section and line.strip() == '# خلاصه دقیق برنامه درسی':
                simplified_lines.append(line)
        
        # اگر آمار کلی پیدا نشد، محتوای اصلی را نگه داریم
        if not simplified_lines or len(simplified_lines) < 3:
            # ایجاد آمار کلی ساده
            simplified_lines = [
                '# خلاصه آماری برنامه درسی',
                '',
                '## آمار کلی',
                '',
                '| معیار | مقدار |',
                '| ----- | ----- |',
                '| اطلاعات آماری | به زودی اضافه خواهد شد |',
                ''
            ]
        
        # اضافه کردن توضیح پایانی
        simplified_lines.append('\n> **نکته**: برای مشاهده جزئیات کامل هر درس، به [جداول خلاصه](summary-tables) مراجعه کنید.')
        
        # نوشتن فایل ساده شده
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(simplified_lines))
        
        print(f"✅ Simplified detailed-summary: {file_path}")
        
    except Exception as e:
        print(f"⚠️  Could not simplify detailed-summary: {str(e)}")

def main():
    """تابع اصلی اجرای برنامه"""
    print("🔍 Starting DS Course Parser...")
    
    try:
        # 1. پارس کردن فایل
        parser = DSCourseParser('../input/DS-Chart.md')
        df = parser.parse_file()
        
        if df is None or len(df) == 0:
            print("❌ No data extracted!")
            return None
        
        # 2. تولید فایل‌های Markdown برای هر درس
        print("\n📝 Generating individual course files...")
        generator = DocusaurusMarkdownGenerator('./docs/curriculum/')
        generator.generate_files(df)
        
        # 3. تولید جداول خلاصه
        print("\n📊 Generating summary tables...")
        summary_gen = SummaryTableGenerator('./docs/curriculum/')
        
        # جدول خلاصه اصلی
        summary_file = summary_gen.generate_summary_tables(
            df, 
            output_file='./docs/summary-tables.md'
        )
        
        # 4. به‌روزرسانی Anchorها در summary-tables
        _update_summary_tables_anchors(summary_file)
        
        # خلاصه دقیق (ابتدا کامل تولید می‌شود، سپس ساده می‌شود)
        detailed_file = './docs/detailed-summary.md'
        
        # 5. ایجاد detailed-summary ساده شده
        _simplify_detailed_summary(detailed_file)
        
        # 6. تولید index.md برای داکساروس
        _generate_index_file(df, summary_file, detailed_file)
        
        # 7. تولید README برای پوشه docs
        _generate_docs_readme(df)
        
        # 8. تولید فایل _category_.json برای دسته‌بندی
        _generate_category_json()
        
        print("\n" + "="*50)
        print("✅ All processes completed successfully!")
        print("="*50)
        print(f"📁 Course files: ./docs/curriculum/")
        print(f"📄 Summary tables (with anchors): {summary_file}")
        print(f"📄 Detailed summary (simplified): {detailed_file}")
        print(f"📄 Index file: ./docs/index.md")
        print(f"📄 Docs README: ./docs/README.md")
        print(f"📄 Category config: ./docs/curriculum/_category_.json")
        print("="*50)
        print("\n📌 Important: Anchor links in summary-tables.md have been updated")
        print("📌 Important: detailed-summary.md contains only statistics")
        print("="*50)
        
        return df
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def _generate_docs_readme(df: pd.DataFrame) -> None:
    """تولید فایل README برای پوشه docs"""
    readme_content = """# مستندات برنامه درسی علوم داده

این پوشه حاوی تمام مستندات تولید شده برای برنامه درسی علوم داده می‌باشد.

## فایل‌های موجود

### 1. فایل‌های درسی (`curriculum/`)
هر درس در یک فایل Markdown جداگانه قرار دارد که به صورت خودکار در دسته‌بندی "برنامه درسی" سازماندهی شده‌اند.

### 2. جداول خلاصه (`summary-tables.md`)
جداول طبقه‌بندی شده بر اساس نوع درس با لینک به صفحات هر درس. دارای Anchorهای مستقیم برای دسترسی سریع.

### 3. خلاصه آماری (`detailed-summary.md`)
آمار کلی برنامه درسی شامل تعداد درس‌ها، واحدها و سایر اطلاعات آماری.

### 4. صفحه اصلی (`index.md`)
صفحه اصلی با دسترسی سریع به تمام بخش‌ها.

## ساختار
docs/
├── curriculum/ # فایل‌های درسی (دسته‌بندی شده)
│ ├── base/ # دروس پایه
│ ├── mandatory/ # دروس الزامی
│ ├── elective/ # دروس اختیاری
│ ├── skill/ # دروس مهارتی
│ ├── other/ # دروس بدون نوع
│ └── category.json # پیکربندی دسته‌بندی
├── summary-tables.md # جداول خلاصه با Anchorها
├── detailed-summary.md # آمار کلی
├── index.md # صفحه اصلی
└── README.md # این فایل

## Anchorهای مستقیم

برای دسترسی سریع به بخش‌های مختلف جداول خلاصه:

- `/docs/summary-tables#base-courses` - دروس پایه
- `/docs/summary-tables#mandatory-courses` - دروس الزامی
- `/docs/summary-tables#elective-courses` - دروس اختیاری
- `/docs/summary-tables#skill-courses` - دروس مهارتی
- `/docs/summary-tables#other-courses` - دروس بدون نوع

## نحوه استفاده

این فایل‌ها به صورت خودکار در سایت Docusaurus نمایش داده می‌شوند.

---
*این مستندات به صورت خودکار تولید شده‌اند.*
"""
    
    os.makedirs('./docs', exist_ok=True)
    with open('./docs/README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("✅ Docs README generated: ./docs/README.md")

def _generate_category_json() -> None:
    """تولید فایل _category_.json برای دسته‌بندی Docusaurus"""
    category_content = {
        "label": "برنامه درسی",
        "position": 2,
        "link": {
            "type": "generated-index",
            "description": "برنامه درسی کامل رشته علوم داده",
            "slug": "/category/برنامه-درسی"
        },
        "collapsed": False
    }
    
    os.makedirs('./docs/curriculum', exist_ok=True)
    import json
    with open('./docs/curriculum/_category_.json', 'w', encoding='utf-8') as f:
        json.dump(category_content, f, ensure_ascii=False, indent=2)
    
    print("✅ Category config generated: ./docs/curriculum/_category_.json")

if __name__ == "__main__":
    main()