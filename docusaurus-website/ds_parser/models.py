# ds_parser/models.py
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Course:
    """مدل داده برای یک درس"""
    fa_title: str = ""
    en_title: str = ""
    prerequisites: str = "ندارد"
    corequisites: str = "ندارد"
    units: str = ""
    hours: str = ""
    has_exercises: str = ""
    course_type: str = ""
    unit_type: str = "نظری"
    goals: str = ""
    competencies: str = ""
    syllabus: str = ""
    teaching_strategies: str = ""
    teaching_methods: str = ""
    assessment_methods: str = ""
    equipment: str = ""
    references: List[str] = field(default_factory=list)
    en_file_name: str = ""
    c_cat: str = ""
    position: int = 0
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Course':
        """ایجاد Course از دیکشنری"""
        course = cls()
        for key, value in data.items():
            if hasattr(course, key):
                setattr(course, key, value)
        return course
    
    def to_dict(self) -> dict:
        """تبدیل Course به دیکشنری"""
        return {key: getattr(self, key) for key in self.__annotations__.keys() if hasattr(self, key)}