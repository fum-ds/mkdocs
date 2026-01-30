# test_parser.py
import unittest
import pandas as pd
from ds_parser import DSCourseParser

class TestDSCourseParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = DSCourseParser('../input/DS-Chart.md')
    
    def test_parse_file(self):
        df = self.parser.parse_file()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
    
    def test_course_types(self):
        df = self.parser.parse_file()
        expected_types = ['پایه', 'تخصصی الزامی', 'تخصصی اختیاری', 'مهارتی']
        actual_types = df['course_type'].unique()
        
        for expected in expected_types:
            self.assertIn(expected, actual_types)
    
    def test_has_exercises(self):
        df = self.parser.parse_file()
        # بررسی که حداقل یک درس حل تمرین دارد
        self.assertTrue((df['has_exercises'] == 'دارد').any())
        # بررسی که حداقل یک درس حل تمرین ندارد
        self.assertTrue((df['has_exercises'] == 'ندارد').any())

if __name__ == '__main__':
    unittest.main()