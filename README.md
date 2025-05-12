🧠 Elective Matcher Portal
🎓 A smart Django-powered portal for managing elective subject choices vs allocations — with automatic mismatch detection and dashboard views for both admins and students.

✨ Key Features
✅ Feature	📋 Description
📥 Student Elective Submission	Students log in and submit their preferred elective subjects
📤 Admin Allocation Upload	Admin uploads the final allocation Excel file
❌ Mismatch Detection	System detects mismatches between student choices and admin allocations
📊 Result Dashboard	Students view their personal result — matched/mismatched electives
🧑‍💼 Admin Dashboard	Admin can view all students and a list of mismatches
🧾 Excel Uploads	Both elective choices and allocations are managed via .xlsx files
💌 Auto Emailing	Credentials sent automatically to students after account creation
🎨 Tailwind UI	Clean, modern UI styled with Tailwind CSS

🧰 Tech Stack
Layer	Technology
🌐 Frontend	Tailwind CSS (via CDN)
⚙️ Backend	Django 5.2
💾 Database	MongoDB Atlas
📊 Data Processing	Pandas, OpenPyXL
✉️ Emailing	Django Email Backend (Console or SMTP)

🔄 Workflow
🧑‍🏫 Admin uploads student email list via Excel

🔐 System generates passwords and emails credentials to students

👨‍🎓 Students log in and submit their elective choices

🧑‍💼 Admin uploads allocation file (final subject allocations)

🔍 System matches choices vs allocations and finds mismatches

📜 Students view their result in their dashboard

📑 Admin reviews mismatch reports on a structured dashboard

🎯 Roles
🧑‍🏫 Admin
Upload student emails

Upload allocation Excel file

View student details and mismatch reports

👨‍🎓 Student
Log in using credentials received via email

Submit elective choices

View matched and mismatched electives

🖥️ UI Preview
🎨 Beautiful Tailwind-based design

📊 Responsive tables

✅ Match/Mismatch highlights

📤 Upload dashboards

🔐 Secure login for both roles

🚀 Getting Started
# Clone the repo
git clone https://github.com/your-username/elective-matcher.git
cd elective-matcher

# Activate virtualenv
source env/bin/activate  # or venv\Scripts\activate (Windows)

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Start server
python manage.py runserver

🛂 Admin Login
Default Email: admin@example.com

Default Password: admin123 (set via createsuperuser or config)

📬 Email System
Currently uses Console Backend (prints email to terminal): EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
You can switch to SMTP to send real emails.

🧪 Test Files Format
🧑‍🎓 Student Emails Excel:
Email
student1@example.com
student2@example.com

📝 Allocation Excel:
Roll No	Elective 1	Elective 2	...

Contributors: Kushal Das(kushal-a11y)
              Arghya Dey(Phenix8240)
