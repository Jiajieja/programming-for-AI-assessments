"""
FILE: test.py
DESCRIPTION:
    Unit tests for the business logic in app/analytics.py.
    Follows TDD principles by mocking external dependencies (Database) 
    to test the algorithms in isolation.

USAGE:
    Run from the project root directory:
    python -m unittest test.py
"""

import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import sys
import os

# Ensure we can import from the app directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the module to be tested
from app import analytics

class TestAnalytics(unittest.TestCase):

    def setUp(self):
        """Set up runs before every test method."""
        pass

    # -------------------------------------------------------------------------
    # Test Suite 1: Wellbeing Analysis (check_at_risk_students)
    # -------------------------------------------------------------------------

    @patch('app.analytics.db_manager')
    def test_check_at_risk_students_filters_correctly(self, mock_db_manager):
        """
        Test that the function correctly filters students with stress_level >= threshold.
        """
        # 1. Mock the database return data
        mock_data = [
            {'student_id': 'S001', 'stress_level': 5, 'sleep_hours': 5, 'date': '2023-10-01'}, # At Risk
            {'student_id': 'S002', 'stress_level': 2, 'sleep_hours': 8, 'date': '2023-10-01'}, # Safe
            {'student_id': 'S003', 'stress_level': 4, 'sleep_hours': 6, 'date': '2023-10-01'}, # At Risk (Threshold inclusive)
        ]
        mock_db_manager.get_raw_survey_data.return_value = mock_data

        # 2. Call the function (visualize=False to prevent plot windows)
        result_df = analytics.check_at_risk_students(stress_threshold=4, visualize=False)

        # 3. Assertions
        self.assertIsInstance(result_df, pd.DataFrame)
        self.assertEqual(len(result_df), 2, "Should return exactly 2 at-risk students")
        
        # Verify specific IDs are present
        at_risk_ids = result_df['student_id'].tolist()
        self.assertIn('S001', at_risk_ids)
        self.assertIn('S003', at_risk_ids)
        self.assertNotIn('S002', at_risk_ids)

    @patch('app.analytics.db_manager')
    def test_check_at_risk_students_empty_db(self, mock_db_manager):
        """
        Test behavior when database returns no data.
        Should return an empty DataFrame with correct columns, not crash.
        """
        mock_db_manager.get_raw_survey_data.return_value = []

        result_df = analytics.check_at_risk_students(visualize=False)

        self.assertTrue(result_df.empty)
        self.assertIn('student_id', result_df.columns)
        self.assertIn('Is_At_Risk', result_df.columns)

    @patch('app.analytics.db_manager')
    def test_check_at_risk_students_deduplication(self, mock_db_manager):
        """
        Test that if a student has multiple entries, we only get the latest one
        if they are at risk.
        """
        mock_data = [
            # Old entry, low stress
            {'student_id': 'S001', 'stress_level': 2, 'sleep_hours': 8, 'date': '2023-09-01'}, 
            # New entry, high stress
            {'student_id': 'S001', 'stress_level': 5, 'sleep_hours': 4, 'date': '2023-10-01'}, 
        ]
        mock_db_manager.get_raw_survey_data.return_value = mock_data

        result_df = analytics.check_at_risk_students(stress_threshold=4, visualize=False)

        self.assertEqual(len(result_df), 1)
        self.assertEqual(result_df.iloc[0]['stress_level'], 5)
        self.assertEqual(result_df.iloc[0]['date'], pd.Timestamp('2023-10-01'))

    # -------------------------------------------------------------------------
    # Test Suite 2: Attendance vs Grades (calculate_attendance_vs_grades)
    # -------------------------------------------------------------------------

    @patch('app.analytics.db_manager')
    def test_calculate_attendance_vs_grades_positive_correlation(self, mock_db_manager):
        """
        Test the logic connecting attendance, grades, and enrollment.
        Scenario: High attendance matches high grades (Positive Correlation).
        """
        # 1. Mock Attendance and Grade Data (get_analytics_data)
        # S001: Present (100%), Score 90
        # S002: Absent (0%), Score 20
        att_data = [
            {'student_id': 'S001', 'status': 'Present', 'date': '2023-01-01'},
            {'student_id': 'S002', 'status': 'Absent', 'date': '2023-01-01'}
        ]
        
        # FIX: Removed 'course_id' from grade_data to prevent merge collision
        # The merge with Enrollment table will add the course_id correctly.
        grade_data = [
            {'student_id': 'S001', 'score': 90},
            {'student_id': 'S002', 'score': 20}
        ]
        mock_db_manager.get_analytics_data.return_value = (att_data, grade_data)

        # 2. Mock SQL Queries (Enrollment and Courses)
        mock_conn = MagicMock()
        mock_db_manager.get_connection.return_value = mock_conn
        
        # side_effect for fetchall():
        # Call 1: Enrollment Table (student_id, course_id)
        # Call 2: Courses Table (id, name)
        mock_conn.execute.return_value.fetchall.side_effect = [
            [('S001', 'C101'), ('S002', 'C101')], # Enrollment data
            [('C101', 'Python Programming')]      # Courses data
        ]

        # 3. Execute Logic
        results = analytics.calculate_attendance_vs_grades(visualize=False)

        # 4. Assertions
        self.assertIsNotNone(results['Global_Correlation_R'])
        self.assertAlmostEqual(results['Global_Correlation_R'], 1.0, places=2)

        # Check per-course correlation
        course_df = results['Per_Course_Correlation']
        self.assertFalse(course_df.empty)
        math_row = course_df[course_df['course_id'] == 'C101'].iloc[0]
        self.assertEqual(math_row['course_name'], 'Python Programming')
        self.assertAlmostEqual(math_row['Correlation_R'], 1.0, places=2)

    @patch('app.analytics.db_manager')
    def test_calculate_attendance_vs_grades_insufficient_data(self, mock_db_manager):
        """
        Test that correlation returns None if there is not enough data 
        (correlation requires at least 2 data points).
        """
        # Only 1 student
        att_data = [{'student_id': 'S001', 'status': 'Present', 'date': '2023-01-01'}]
        
        # FIX: Removed 'course_id' here as well
        grade_data = [{'student_id': 'S001', 'score': 90}]
        
        mock_db_manager.get_analytics_data.return_value = (att_data, grade_data)

        mock_conn = MagicMock()
        mock_db_manager.get_connection.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.side_effect = [
            [('S001', 'C101')],         # Enrollment
            [('C101', 'Python Prog')]   # Courses
        ]

        results = analytics.calculate_attendance_vs_grades(visualize=False)

        self.assertIsNone(results['Global_Correlation_R'])
        
        course_df = results['Per_Course_Correlation']
        # The correlation should be None (or NaN) because there's only 1 data point
        self.assertIsNone(course_df.iloc[0]['Correlation_R'])

if __name__ == '__main__':
    unittest.main()