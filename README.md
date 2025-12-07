# programming-for-AI-assessments
Group assessment for PAI module

## How to Run the Project
### Prerequisites
- Python 3.10+ installed on your system (use <code>`python3 --version`</code> to check).
- Recommended: create and activate a virtual environment:
<pre>
<code>
  python3 -m venv venv
  source venv/bin/activate   # On macOS/Linux
  venv\Scripts\activate      # On Windows
</code>
</pre>

### Running the Application
<pre>
<code>
python3 main.py
</code>
</pre>

### Run unit tests
<pre>
<code>
python3 test_analytics_data.py
python3 test_analytics.py
python3 test_registration.py
python3 test_run.py
</code>
</pre>

## Assessment Task:
You will receive a scenario that outlines a particular domain challenge. Based on the scenario, your group must:
1.	Design a Software Solution:
- Analyse the scenario and identify user requirements
- Design and develop an appropriate software architecture
- Design and implement a relational database schema
- Build a software application in Python3 that solves the given problem and interacts effectively with the database
2.	Collaborate as a Development Team:
- Use version control and project management tools to coordinate tasks
- Ensure contributions are fairly distributed and well-documented
- Demonstrate good coding practices, testing supported by research, and documentation
3.	Apply and Reflect on a Software Development Lifecycle:
- Select and apply an appropriate SDLC methodology 
- Document and critically evaluate your process
- Reflect on challenges, decisions, and lessons learned
4.	Deliver a Live Presentation and Demonstration:
- Prepare PowerPoint slides and present your project to the class, highlighting features, technologies used, software development documentation (e.g. ER and UML diagrams), and development methodology
- Demonstrate your working software
- Respond to questions about design decisions and implementation

## Assessment Scenario:
The university is exploring ways to better understand and support student wellbeing. At present, data such as lecture attendance, coursework submissions, and optional weekly wellbeing surveys are collected separately, but there is no single system to combine or analyse these data sources.
The Student Wellbeing Office has therefore asked your development team to design and implement a small prototype system. The system should:
1.	Collect and store data according to your requirement analysis – e.g. weekly attendance, submission deadlines, survey responses (e.g. stress levels 1–5, hours slept).
2.	Provide simple analytics – e.g. calculate average attendance per student, identify weeks with higher stress levels, or visualise changes over time.
3.	Allow the authorised users to create, read, update and delete (CRUD) the data.
The prototype does not need to be production-ready. Still, it should demonstrate how such a system could be developed in Python, with a relational database backend, and include some simple data analysis and visualisation features.