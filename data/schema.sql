-- database: :memory:
-- 1. Enable Foreign Key support (SQLite defaults to OFF)
PRAGMA foreign_keys = OFF;

-- 2. Clean up old tables (for development/testing purposes)
DROP TABLE IF EXISTS Wellbeing_Surveys;
DROP TABLE IF EXISTS Submissions;
DROP TABLE IF EXISTS Attendance;
DROP TABLE IF EXISTS Enrollment;
DROP TABLE IF EXISTS Assessments;
DROP TABLE IF EXISTS Students;
DROP TABLE IF EXISTS Course_directors;
DROP TABLE IF EXISTS Users;
DROP TABLE IF EXISTS Surveys;
DROP TABLE IF EXISTS Courses;
DROP TABLE IF EXISTS Roles;

-- to check foreign key constraints
PRAGMA foreign_keys = ON;

-- 3. Table Definitions

-- Table: Roles
-- Contains information about user roles (reference table)
CREATE TABLE Roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

-- Table: Users
-- Stores basic information for users
CREATE TABLE Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role_id INTEGER NOT NULL,
    FOREIGN KEY (role_id) REFERENCES Roles(id)
);

-- Table: Courses
-- Contains information about courses (reference table)
-- A separate table for courses, in case the course name needs to be changed in the future (for example)
CREATE TABLE Courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

-- Table: Course_directors
-- Table linking the course and the course director (user)
CREATE TABLE Course_directors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (course_id) REFERENCES Courses(id),
    UNIQUE(user_id, course_id)
);

-- Table: Students
-- Stores basic identification for students
CREATE TABLE Students (
    id INTEGER PRIMARY KEY,
    graduation_date DATE NOT NULL,
    status TEXT CHECK(status IN ('Active', 'Inactive'))
);

-- Table: Enrollment
-- Links students to courses
CREATE TABLE Enrollment (
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    PRIMARY KEY (student_id, course_id),
    FOREIGN KEY (course_id) REFERENCES Courses(id),
    FOREIGN KEY (student_id) REFERENCES Students(id)
);

-- Table: Assessments
-- Defines coursework or exams with deadlines
CREATE TABLE Assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    course_id INTEGER NOT NULL,
    deadline DATE NOT NULL,
    max_score INTEGER DEFAULT 100,
    FOREIGN KEY (course_id) REFERENCES Courses(id)
);

-- Table: Attendance
-- Tracks weekly lecture attendance
CREATE TABLE Attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    lecture_date DATE NOT NULL,
    status TEXT CHECK(status IN ('Present', 'Absent', 'Late')),
    FOREIGN KEY (student_id) REFERENCES Students(id),
    FOREIGN KEY (course_id) REFERENCES Courses(id),
    UNIQUE(student_id, course_id, lecture_date)
);

-- Table: Submissions
-- Links assessments to students and records grades
-- This data supports the Course Director's need for performance analytics
CREATE TABLE Submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    submission_date DATE,
    score REAL CHECK(score >= 0),
    FOREIGN KEY (assessment_id) REFERENCES Assessments(id),
    FOREIGN KEY (student_id) REFERENCES Students(id),
    UNIQUE(student_id, assessment_id)
);

-- Table: Surveys
-- Contains information about surveys (reference table)
CREATE TABLE Surveys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    passed_date DATE NOT NULL
);

-- Table: Wellbeing_Surveys
-- Stores weekly survey responses
-- Includes constraint: Stress levels must be 1-5
CREATE TABLE Wellbeing_Surveys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    survey_id INTEGER NOT NULL,
    stress_level INTEGER CHECK(stress_level BETWEEN 1 AND 5), 
    sleep_hours REAL CHECK(sleep_hours >= 0),
    FOREIGN KEY (student_id) REFERENCES Students(id),
    FOREIGN KEY (survey_id) REFERENCES Surveys(id),
    UNIQUE(student_id, survey_id)
);

-- 4. Insert Mock Data (for demonstration)

-- Insert Roles
INSERT INTO Roles (name) VALUES 
('Student Wellbeing Officer'),
('Student Wellbeing Officer Team'),
('Course Director');

-- Insert Users
INSERT INTO Users (username, password, role_id) VALUES 
('will_b', 'test123', 1),
('mike_w', 'test123', 2),
('lucas_s', 'test123', 3),
('dustin_h', 'test123', 3), 
('steve_h', 'test123', 3); 

-- Insert Courses
INSERT INTO Courses (name) VALUES 
('Applied Statistics for AI'),
('Programming for AI'),
('FAIR');

INSERT INTO Course_directors (user_id, course_id) VALUES 
(3, 1),
(4, 2),
(5, 3);

-- Insert Students
INSERT INTO Students (id, graduation_date, status) VALUES 
(575001, '2026-10-01', 'Active'),
(575002, '2026-10-01', 'Active'),
(575003, '2024-10-01', 'Active'),
(575004, '2026-10-01', 'Active'),
(575005, '2026-10-01', 'Active'),
(575006, '2026-10-01', 'Inactive'),
(575007, '2026-10-01', 'Active'),
(575008, '2026-10-01', 'Active'),
(575009, '2026-10-01', 'Active'),
(575010, '2026-10-01', 'Active'),
(575011, '2026-10-01', 'Inactive'),
(575012, '2025-10-01', 'Active'),
(575013, '2025-10-01', 'Active'),
(575014, '2026-10-01', 'Active'),
(575015, '2026-10-01', 'Active'),
(575016, '2026-10-01', 'Active'),
(575017, '2024-10-01', 'Inactive'),
(575018, '2026-10-01', 'Active'),
(575019, '2026-10-01', 'Active'),
(575020, '2026-10-01', 'Active');

-- Insert Enrollment
INSERT INTO Enrollment (student_id, course_id) VALUES 
(575001, 1), (575001, 2), (575001, 3),
(575002, 1), (575002, 2), (575002, 3),
(575003, 1), (575003, 2), (575003, 3),
(575004, 1), (575004, 2),
(575005, 1), (575005, 2),
(575006, 3),
(575007, 1), (575007, 2), (575007, 3),
(575008, 3),
(575009, 1), (575009, 2),
(575010, 1), (575010, 3),
(575011, 3),
(575012, 2), (575012, 3),
(575013, 1), (575013, 2), (575013, 3),
(575014, 2),
(575015, 1),
(575016, 1), (575016, 3),
(575017, 3),
(575018, 1), (575018, 2),
(575019, 1), (575019, 2), (575019, 3),
(575020, 2), (575020, 3);

-- Insert Assessments
INSERT INTO Assessments (title, course_id, deadline, max_score) VALUES 
('Python Project', 2, '2025-11-30', 100), -- for Programming for AI
('Data Analysis Essay', 3, '2025-12-15', 50), -- for FAIR
('ANOVA Project', 1, '2025-12-15', 100), -- for Applied Statistics for AI
('Project Euler Challenge', 2, '2025-12-20', 100),
('Research Paper: AI Ethics', 3, '2025-12-22', 70),
('Machine Learning Quiz 1', 1, '2025-10-30', 20),
('Machine Learning Quiz 2', 1, '2025-11-20', 20),
('Coding Lab 1', 2, '2025-10-15', 30),
('Coding Lab 2', 2, '2025-11-01', 30),
('FAIR Presentation', 3, '2025-11-10', 50);

-- Insert Submissions
INSERT INTO Submissions (assessment_id, student_id, submission_date, score) VALUES 
(1, 575001, '2025-11-15', 90), -- Python Project, 2
(1, 575002, '2025-11-16', 80), 
(1, 575003, '2025-11-15', 70), 
(1, 575004, '2025-11-15', 60),
(1, 575005, '2025-11-30', 30), -- failed
(2, 575001, '2025-12-15', 80), -- Data Analysis Essay, 3
(2, 575002, '2025-12-15', 80),
(2, 575003, '2025-12-14', 0), -- failed
(3, 575001, '2025-12-15', 70), -- ANOVA Project, 1
(3, 575003, '2025-12-18', 40),
(3, 575007, '2025-12-15', 0), -- failed
(4, 575001, '2025-10-29', 18), -- Quiz 1
(4, 575002, '2025-10-30', 15),
(4, 575003, '2025-10-30', 12),
(4, 575009, '2025-10-26', 10),
(4, 575010, '2025-10-27', 20),
(5, 575001, '2025-11-18', 20), -- Quiz 2
(5, 575002, '2025-11-19', 17),
(5, 575003, '2025-11-20', 14),
(5, 575009, '2025-11-20', 10),
(6, 575012, '2025-10-14', 28), -- Coding Lab 1
(6, 575013, '2025-10-14', 25),
(6, 575014, '2025-10-15', 20),
(6, 575020, '2025-10-15', 29),
(7, 575013, '2025-10-31', 28), -- Coding Lab 2
(7, 575014, '2025-11-01', 24),
(7, 575020, '2025-11-01', 27),
(8, 575009, '2025-11-10', 45), -- FAIR Presentation
(8, 575019, '2025-11-09', 40),
(8, 575020, '2025-11-10', 42);

-- Insert Attendance
INSERT INTO Attendance (student_id, course_id, lecture_date, status) VALUES 
(575001, 1, '2025-10-01', 'Present'),
(575002, 1, '2025-10-08', 'Present'),
(575003, 1, '2025-10-08', 'Present'),
(575004, 1, '2025-10-08', 'Present'),
(575005, 1, '2025-10-08', 'Present'),
(575007, 1, '2025-10-08', 'Absent'),
(575001, 2, '2025-10-01', 'Absent'),
(575002, 2, '2025-10-01', 'Present'),
(575007, 2, '2025-10-08', 'Absent'),
(575007, 3, '2025-10-08', 'Absent'),
(575006, 3, '2025-10-01', 'Present'),
(575009, 1, '2025-10-01', 'Present'),
(575009, 1, '2025-10-08', 'Late'),
(575009, 2, '2025-10-08', 'Absent'),
(575010, 1, '2025-10-01', 'Late'),
(575010, 3, '2025-10-01', 'Present'),
(575010, 3, '2025-10-08', 'Present'),
(575012, 2, '2025-10-15', 'Present'),
(575012, 2, '2025-10-22', 'Absent'),
(575012, 3, '2025-10-22', 'Late'),
(575013, 1, '2025-10-01', 'Present'),
(575013, 2, '2025-10-01', 'Present'),
(575013, 3, '2025-10-01', 'Present'),
(575013, 1, '2025-10-08', 'Absent'),
(575013, 2, '2025-10-15', 'Late'),
(575013, 3, '2025-10-15', 'Present'),
(575018, 1, '2025-10-01', 'Present'),
(575018, 1, '2025-10-08', 'Present'),
(575018, 2, '2025-10-08', 'Late'),
(575019, 1, '2025-10-01', 'Absent'),
(575019, 2, '2025-10-01', 'Present'),
(575019, 3, '2025-10-01', 'Present'),
(575019, 1, '2025-10-08', 'Present'),
(575019, 2, '2025-10-08', 'Present'),
(575019, 3, '2025-10-08', 'Absent');

-- Insert Surveys
INSERT INTO Surveys (passed_date) VALUES 
('2025-12-01'),
('2025-12-07'),
('2025-12-14'),
('2025-12-21'),
('2025-12-28'),
('2026-01-04'),
('2026-01-11'),
('2026-01-18'),
('2026-01-25');

-- Insert Wellbeing Surveys
-- Simulating a high-stress scenario for the Wellbeing Officer to detect
INSERT INTO Wellbeing_Surveys (student_id, survey_id, stress_level, sleep_hours) VALUES 
(575001, 1, 2, 7.5), -- Normal entry
(575002, 2, 5, 4.0), -- High stress
(575002, 3, 4, 5.0), -- High stress continued
(575003, 1, 4, 6.0),
(575003, 2, 4, 4.0),
(575001, 2, 1, 8.0),
(575009, 4, 2, 7.0),
(575009, 5, 2, 7.5),
(575009, 6, 3, 7.0),
(575013, 4, 3, 6.0),
(575013, 5, 4, 5.5),
(575013, 6, 5, 5.0),
(575019, 4, 5, 4.0),
(575019, 5, 2, 7.0),
(575019, 6, 4, 6.0),
(575012, 4, 3, 4.0),
(575012, 5, 4, 3.5),
(575012, 6, 4, 3.0);