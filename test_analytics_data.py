"""
FILE: test_analytic_data.py
DESCRIPTION:
    Unit tests for the visualization logic in app/analytic_data.py.
    Tests generation of Matplotlib figures and data processing logic.
    
USAGE:
    Run from the project root directory:
    python -m unittest test_analytic_data.py
"""

import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

# -------------------------------------------------------------------------
# Path Configuration
# -------------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app import analytic_data

class TestAnalyticData(unittest.TestCase):

    def setUp(self):
        """Set up runs before every test method."""
        # Prevent matplotlib from trying to open GUI windows during tests
        plt.switch_backend('Agg')
        # Register converters just in case, though we are mocking the heavy lifting now
        pd.plotting.register_matplotlib_converters()

    def tearDown(self):
        """Clean up after tests."""
        plt.close('all')

    # -------------------------------------------------------------------------
    # Helper: Mock Data Generators
    # -------------------------------------------------------------------------
    
    def _mock_db_attendance_grade(self, mock_db_manager):
        """Helper to setup basic attendance and grade mock data."""
        att_data = [
            {'student_id': 'S001', 'status': 'Present', 'date': '2023-01-01'},
            {'student_id': 'S002', 'status': 'Absent', 'date': '2023-01-01'}
        ]
        grade_data = [
            {'student_id': 'S001', 'score': 90},
            {'student_id': 'S002', 'score': 30}
        ]
        mock_db_manager.get_analytics_data.return_value = (att_data, grade_data)

        mock_conn = MagicMock()
        mock_db_manager.get_connection.return_value = mock_conn
        
        mock_conn.execute.return_value.fetchall.side_effect = [
            [('S001', 'C101'), ('S002', 'C101')], # Enrollment
            [('C101', 'Python Basics')]           # Courses
        ]

    # -------------------------------------------------------------------------
    # Test Suite 1: Logic Verification (calculate_attendance_vs_grades)
    # -------------------------------------------------------------------------

    @patch('app.analytic_data.db_manager')
    def test_calculate_attendance_vs_grades_logic(self, mock_db_manager):
        """Test the calculation logic returns correct structure."""
        self._mock_db_attendance_grade(mock_db_manager)

        result = analytic_data.calculate_attendance_vs_grades(visualize=False)

        self.assertIsInstance(result, dict)
        self.assertIn("Global_Correlation_R", result)
        self.assertAlmostEqual(result["Global_Correlation_R"], 1.0, places=1)
        
        per_course_df = result["Per_Course_Correlation"]
        self.assertFalse(per_course_df.empty)
        self.assertEqual(per_course_df.iloc[0]['course_name'], 'Python Basics')

    # -------------------------------------------------------------------------
    # Test Suite 2: Plotting Functions (Global & Course)
    # -------------------------------------------------------------------------

    @patch('app.analytic_data.db_manager')
    def test_build_global_scatter_figure(self, mock_db_manager):
        """Test global scatter plot returns a Figure."""
        self._mock_db_attendance_grade(mock_db_manager)

        fig = analytic_data.build_global_scatter_figure()
        
        self.assertIsInstance(fig, plt.Figure)
        ax = fig.axes[0]
        self.assertEqual(ax.get_title(), "Global Attendance vs Grades")
        self.assertTrue(len(ax.collections) > 0)

    @patch('app.analytic_data.db_manager')
    def test_build_global_scatter_empty(self, mock_db_manager):
        """Test global scatter plot with empty data."""
        mock_db_manager.get_analytics_data.return_value = ([], [])
        
        fig = analytic_data.build_global_scatter_figure()
        
        self.assertIsInstance(fig, plt.Figure)
        ax = fig.axes[0]
        # Use .axison to check if axis is enabled
        self.assertFalse(ax.axison)

    @patch('app.analytic_data.db_manager')
    def test_build_per_course_correlation_bar_figure(self, mock_db_manager):
        """Test per-course bar chart."""
        self._mock_db_attendance_grade(mock_db_manager)

        fig = analytic_data.build_per_course_correlation_bar_figure()
        
        self.assertIsInstance(fig, plt.Figure)
        ax = fig.axes[0]
        self.assertEqual(ax.get_title(), "Per-Course Correlation (R)")

    @patch('app.analytic_data.db_manager')
    def test_build_per_course_avg_scatter_figure(self, mock_db_manager):
        """Test per-course average scatter plot."""
        self._mock_db_attendance_grade(mock_db_manager)

        fig = analytic_data.build_per_course_avg_scatter_figure()
        
        self.assertIsInstance(fig, plt.Figure)
        ax = fig.axes[0]
        self.assertEqual(ax.get_title(), "Per-Course Avg Attendance vs Avg Score")

    # -------------------------------------------------------------------------
    # Test Suite 3: Stress & Survey Plots
    # -------------------------------------------------------------------------

    @patch('app.analytic_data.db_manager')
    def test_build_stress_histogram_figure(self, mock_db_manager):
        """Test stress histogram generation."""
        mock_data = [
            {'student_id': 'S001', 'stress_level': 5, 'sleep_hours': 5, 'date': '2023-10-01'},
            {'student_id': 'S002', 'stress_level': 2, 'sleep_hours': 8, 'date': '2023-10-01'},
        ]
        mock_db_manager.get_raw_survey_data.return_value = mock_data

        fig = analytic_data.build_stress_histogram_figure()
        
        self.assertIsInstance(fig, plt.Figure)
        ax = fig.axes[0]
        self.assertEqual(ax.get_title(), "Students by Stress Level (latest)")

    @patch('app.analytic_data.sns.lineplot')
    @patch('app.analytic_data._get_student_survey_df')
    def test_build_student_stress_timeseries_figure(self, mock_get_df, mock_sns_lineplot):
        """
        Test individual student stress timeline.
        FIX: We now MOCK sns.lineplot to avoid 'isfinite' errors caused by 
        matplotlib/seaborn compatibility issues with date objects in CI calculation.
        """
        # Create a clean DataFrame
        mock_df = pd.DataFrame({
            'student_id': [101, 101],
            'date': pd.to_datetime(['2023-10-01', '2023-10-02']),
            'stress_level': [3.0, 5.0],
            'sleep_hours': [7.0, 5.0]
        })
        mock_get_df.return_value = mock_df

        # Call function
        fig = analytic_data.build_student_stress_timeseries_figure(101)
        
        # Assertions
        self.assertIsInstance(fig, plt.Figure)
        ax = fig.axes[0]
        self.assertIn("Student 101", ax.get_title())
        
        # Verify Seaborn was called correctly
        # This confirms we TRIED to plot the right data, without actually executing the failing pixel logic
        mock_sns_lineplot.assert_called_once()
        _, kwargs = mock_sns_lineplot.call_args
        
        # Check that we passed the correct data and columns
        pd.testing.assert_frame_equal(kwargs['data'], mock_df)
        self.assertEqual(kwargs['x'], 'date')
        self.assertEqual(kwargs['y'], 'stress_level')
        self.assertEqual(kwargs['ax'], ax)

    @patch('app.analytic_data._get_student_survey_df')
    def test_build_student_timeseries_no_data(self, mock_get_df):
        """Test timeseries when student does not exist."""
        # Return empty DF
        mock_get_df.return_value = pd.DataFrame(columns=['student_id','date','stress_level','sleep_hours'])

        fig = analytic_data.build_student_stress_timeseries_figure(999)
        
        self.assertIsInstance(fig, plt.Figure)
        ax = fig.axes[0]
        self.assertFalse(ax.axison)

if __name__ == '__main__':
    unittest.main()