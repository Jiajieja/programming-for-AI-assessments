# Requirements Summary

## User Roles
- The system will support three user roles:
  - Student Wellbeing Officer (SWO)
  - Student Wellbeing Team
  - Course Director (CD)
- Each role has different permissions and access levels.

## Data Collection & Management
- The Student Wellbeing Officer and the Wellbeing Team can upload and update student data.
- The system will store the following data:
  - Weekly attendance
  - Coursework submissions / deadlines
  - Wellbeing survey responses (e.g., stress level 1–5, hours slept)
  - “Future-proofing”: the system should allow adding new data categories later.
- To protect student anonymity, only Student ID and Course name will be stored — no personal details.
- Data for graduated students must be removed from the system.
(This implies storing a graduation date or an “active/inactive student” status.)

## Data Access Rules
- Student Wellbeing Officer (SWO):
  - Full access to all student data
  - Can view analytics, statistics, charts, and trends
- Wellbeing Team:
  - Can upload, edit, and manage data
  - Cannot access analytics or dashboards
- Course Director (CD):
  - Can only see data for students in their own course
  - Can view attendance and submission data
  - Does not see any wellbeing survey data (stress levels, hours slept, etc.)

## Analytics & Visualisation
- The system should provide simple, clear analytics, including:
  - Average attendance per student
  - Trends in survey responses (e.g., changes in stress over time)
  - Highlighting students with consistently low attendance, high stress, lack of sleep, or long-term negative patterns
  - Weekly or time-series visualisations (charts, tables, summaries)
- Data Export
  - Both the Student Wellbeing Officer and the Course Director should be able to export the data they have access to.
  - Export format can be simple (e.g., CSV).

## Additional Notes
It’s better to implement one feature well than to overload the prototype with too many options. The system should remain flexible enough to extend in the future (e.g., new data types, new analytics).

# Use cases
| Use Case ID | Use Case Name | Actor(s) | Goal | Preconditions | Trigger | Main Flow (Short) | Postcondition |
|-------------|----------------|-----------|-------|---------------|----------|---------------------|----------------|
| UC01 | Upload Student Data | Student Wellbeing Officer, Wellbeing Team | Upload or update student data | User is authenticated | User selects "Upload data" | 1. Select data type. 2. Upload/enter data. 3. Validate. 4. Save. | Data stored/updated. |
| UC02 | View Full Student Analytics | Student Wellbeing Officer | View all analytics | SWO is logged in | SWO opens dashboard | 1. Open analytics dashboard. 2. View charts, trends, highlights. | Analytics displayed. |
| UC03 | View Course-Level Analytics | Course Director | View attendance + submissions for their course | CD is logged in and linked to a course | CD opens course dashboard | 1. Open dashboard. 2. System shows course data. | Course analytics displayed. |
| UC04 | View Raw Student Data | Student Wellbeing Officer | View all stored data | SWO is logged in | SWO selects student/dataset | 1. Pick dataset. 2. System displays raw data. | Raw data visible. |
| UC05 | Edit Student Data | Student Wellbeing Officer, Wellbeing Team | Modify existing data | User is authenticated; data exists | User selects "Edit" | 1. Select record. 2. Edit. 3. Validate. 4. Save. | Data updated. |
| UC06 | Delete Student Data | Student Wellbeing Officer, Wellbeing Team | Remove incorrect data | User is authenticated; record exists | User selects "Delete" | 1. Select record. 2. Confirm. 3. Delete. | Data removed. |
| UC07 | Remove Graduated Students | System (automatic) | Automatically delete graduated student data | Graduation date/status available | Scheduled system check | 1. Check status. 2. Delete if graduated. | Graduate data removed. |
| UC08 | Export Data | Student Wellbeing Officer, Course Director | Export data they can access | User is authenticated | User selects export option | 1. Choose dataset. 2. Generate file. 3. Download. | Data exported. |
| UC09 | Login & Access Control | All Users | Access system with correct permissions | System online | User attempts login | 1. Enter credentials. 2. Verify. 3. Assign role. | User logged in. |
| UC10 | Add New Data Categories | Student Wellbeing Officer | Add new types of data | SWO authenticated | SWO selects "Manage Data Types" | 1. Add category. 2. System updates metadata. | New category added. |
