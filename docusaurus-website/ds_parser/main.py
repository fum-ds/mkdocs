# ds_parser/main.py
import sys
import os
import pandas as pd
import urllib.parse
from pathlib import Path
from .utils import get_current_timestamp
import json

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

def _generate_index_file(df: pd.DataFrame, summary_file: str, detailed_file: str, generation_time: str) -> None:
    """تولید فایل index.md برای سازماندهی بهتر"""
    
    try:
        # خواندن محتوای فایل preface.md
        preface_content = ""
        preface_path = '../input/preface.md'
        
        if os.path.exists(preface_path):
            with open(preface_path, 'r', encoding='utf-8') as f:
                preface_content = f.read().strip()
            print(f"✅ Read preface content from: {preface_path}")
        else:
            print(f"⚠️  Preface file not found: {preface_path}")
            # محتوای پیش‌فرض
            preface_content = """این بخش شامل اطلاعات کلی درباره برنامه درسی رشته علوم داده می‌باشد.

**توجه**: جداول طبقه‌بندی شده درس‌ها از منوی سمت راست قابل دسترس هستند."""
    
    except Exception as e:
        print(f"⚠️  Error reading preface file: {str(e)}")
        preface_content = """این بخش شامل اطلاعات کلی درباره برنامه درسی رشته علوم داده می‌باشد.

**توجه**: جداول طبقه‌بندی شده درس‌ها از منوی سمت راست قابل دسترس هستند."""
    
    # ساخت محتوای index با preface
    index_content = f"""# برنامه درسی علوم داده

{preface_content}
"""

# ## بخش‌های مختلف

# 1. **[دروس پایه](/docs/category/base/)**: اطلاعات کامل هر درس به صورت جداگانه
# 2. **[دروس الزامی](/docs/category/mandatory/)**: دروس تخصصی الزامی
# 3. **[دروس اختیاری](/docs/category/elective/)**: دروس تخصصی اختیاری
# 4. **[دروس مهارتی](/docs/category/skill/)**: دروس مهارتی و اشتغال‌پذیری
# ## دسترسی سریع     
    # categories = [
    #     ('base', 'دروس پایه'),
    #     ('mandatory', 'دروس الزامی'),
    #     ('elective', 'دروس اختیاری'),
    #     ('skill', 'دروس مهارتی')
    # ]
    
    # for english_slug, persian_title in categories:
    #     index_content += f"1. **[{persian_title}](/docs/category/{english_slug})**: اطلاعات کامل هر درس به صورت جداگانه\n"
    
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
    index_content += f"""
---
**تاریخ تولید**: {generation_time}

*این مستندات به صورت خودکار تولید شده‌اند.*
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


# def fix_category_json_files():
#     base_dir = "docs/category"
    
#     categories = [
#         ("base", "دروس پایه", 2, "دروس پایه رشته علوم داده"),
#         ("mandatory", "دروس الزامی", 3, "دروس تخصصی الزامی"),
#         ("elective", "دروس اختیاری", 4, "دروس تخصصی اختیاری"),
#         ("skill", "دروس مهارتی", 5, "دروس مهارتی و اشتغال‌پذیری")
#     ]
    
#     for slug, label, position, description in categories:
#         dir_path = os.path.join(base_dir, slug)
#         os.makedirs(dir_path, exist_ok=True)
        
#         category_json = {
#             "label": label,
#             "position": position,
#             "link": {
#                 "type": "generated-index",
#                 "description": description,
#                 "slug": f"/category/{slug}"
#             },
#             "collapsed": False
#         }
        
#         file_path = os.path.join(dir_path, "_category_.json")
#         with open(file_path, 'w', encoding='utf-8') as f:
#             json.dump(category_json, f, ensure_ascii=False, indent=2)
        
#         print(f"✅ Created: {file_path}")
    
#     # حذف پوشه curriculum اگر وجود دارد
#     curriculum_path = os.path.join(base_dir, "curriculum")
#     if os.path.exists(curriculum_path):
#         import shutil
#         shutil.rmtree(curriculum_path)
#         print(f"✅ Removed: {curriculum_path}")



def main():
    """تابع اصلی اجرای برنامه"""
    generation_time = get_current_timestamp()
    print(f"🚀 Starting generation at: {generation_time}")
    

    try:
        # fix_category_json_files()
    
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
        summary_file = summary_gen.generate_summary_tables(
            df, 
            output_file='./docs/summary-tables.md'
        )
        
        # 4. تولید index.md با تاریخ
        _generate_index_file(df, summary_file, '', generation_time)
        
        # 5. تولید category configs
        _generate_category_json(generation_time)
        
        # 6. تولید README
        # _generate_docs_readme(df, generation_time)
        

        print("\n" + "="*60)
        print("✅ GENERATION COMPLETE!")
        print("="*60)
        print(f"📅 Generated at: {generation_time}")
        print(f"📚 Total courses: {len(df)}")
        print(f"📁 English folders: base/, mandatory/, elective/, skill/, other/")
        print(f"🌐 Access URLs:")
        print(f"   - /docs/category/curriculum/")
        print(f"   - /docs/category/base/")
        print(f"   - /docs/category/mandatory/")
        print(f"   - /docs/category/elective/")
        print(f"   - /docs/category/skill/")
        print("="*60)
        
        return df
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
def _generate_docs_readme(df: pd.DataFrame, generation_time: str) -> None:
    """تولید فایل repo_structure برای پوشه docs"""
    readme_content = f"""# ساختار فایلهای وبگاه برنامه درسی علوم داده

این فایل‌ها به صورت خودکار توسط اسکریپت Python تولید شده‌اند.

## اطلاعات تولید

- **تاریخ تولید**: {generation_time}
- **تعداد درس‌ها**: {len(df) if df is not None else 'نامشخص'}

## ساختار


```
docs/
├── curriculum/          # فایل‌های درسی اصلی (انگلیسی)
│   ├── base/           # دروس پایه
│   ├── mandatory/      # دروس الزامی  
│   ├── elective/       # دروس اختیاری
│   ├── skill/         # دروس مهارتی
│   └── other/         # سایر دروس
├── category/           # برای نمایش در Docusaurus (symlinks)
│   ├── base/          # -> ../curriculum/base/
│   ├── mandatory/     # -> ../curriculum/mandatory/
│   ├── elective/      # -> ../curriculum/elective/
│   ├── skill/        # -> ../curriculum/skill/
│   └── other/        # -> ../curriculum/other/
├── summary-tables.md   # جداول خلاصه
├── index.md           # صفحه اصلی
└── repo-structure.md  # این فایل
```

---
*این مستندات به صورت خودکار در تاریخ {generation_time} تولید شده‌اند.*
"""
    
    os.makedirs('./docs', exist_ok=True)
    with open('./docs/repo-structure.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ Docs repo-structure generated at: {generation_time}")

def _generate_category_json(generation_time: str) -> None:
    """تولید فایل‌های _category_.json ساده"""
    
    import json
    import os
    
    # فقط فایل‌های ضروری را بساز
    categories = [
        {
            "path": "./docs/curriculum/_category_.json",
            "content": {
                "label": "برنامه درسی",
                "position": 1,
                "link": {
                    "type": "generated-index",
                    "slug": "/category/curriculum"
                },
                "collapsed": False
            }
        },
        {
            "path": "./docs/curriculum/base/_category_.json",
            "content": {
                "label": "دروس پایه",
                "position": 1,
                "collapsed": False
            }
        },
        {
            "path": "./docs/curriculum/mandatory/_category_.json",
            "content": {
                "label": "دروس الزامی",
                "position": 2,
                "collapsed": False
            }
        },
        {
            "path": "./docs/curriculum/skill/_category_.json",
            "content": {
                "label": "دروس مهارتی",
                "position": 3,
                "collapsed": False
            }
        },
        {
            "path": "./docs/curriculum/elective/_category_.json", 
            "content": {
                "label": "دروس اختیاری",
                "position": 4,
                "collapsed": False
            }
        }

    ]
    
    for category in categories:
        os.makedirs(os.path.dirname(category["path"]), exist_ok=True)
        
        with open(category["path"], 'w', encoding='utf-8') as f:
            json.dump(category["content"], f, ensure_ascii=False, indent=2)
        
        print(f"✅ Created: {category['path']}")

if __name__ == "__main__":
    main()