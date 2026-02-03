# ساختار فایلهای وبگاه برنامه درسی علوم داده

این فایل‌ها به صورت خودکار توسط اسکریپت Python تولید شده‌اند.

## اطلاعات تولید

- **تاریخ تولید**: 1404/11/14 - 08:31
- **تعداد درس‌ها**: 37

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
*این مستندات به صورت خودکار در تاریخ 1404/11/14 - 08:31 تولید شده‌اند.*
