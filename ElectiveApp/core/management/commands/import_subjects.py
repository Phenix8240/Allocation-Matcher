import pandas as pd
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from core.models import Subject

class Command(BaseCommand):
    help = 'Import subjects with accurate section handling'

    def handle(self, *args, **kwargs):
        files = [
            (os.path.join(settings.BASE_DIR, 'SubjectData', 'Odd_Semesters.xlsx'), 'ODD'),
            (os.path.join(settings.BASE_DIR, 'SubjectData', 'Subject List even.xlsx'), 'EVEN')
        ]

        # Define all valid section headers from both files
        self.section_headers = {
            'Theory', 'Laboratory', 'Electives', 'Sessional',
            'Practicals', 'Practical', 'Project', 'Prof. Elective IV',
            'Open ElectiveII', 'Elective(PE II)', 'Elective(PE III)',
            'Open Elective (OE III)', 'Elective (PE VI)', 'Open Elective (OEI V)'
        }

        for file_path, sem_type in files:
            try:
                self.stdout.write(f"\n{'#'*40}\nProcessing {os.path.basename(file_path)}\n{'#'*40}")
                df = pd.read_excel(file_path, sheet_name='Sheet1', header=0)
                self.process_file(df, sem_type)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))

        self.stdout.write(self.style.SUCCESS('\nImport completed. Verify counts with:'))
        self.stdout.write(self.style.SUCCESS('python manage.py shell'))
        self.stdout.write(self.style.SUCCESS('from core.models import Subject'))
        self.stdout.write(self.style.SUCCESS('print(Subject.objects.count())'))

    def process_file(self, df, sem_type):
        current_semester = None
        current_section = None

        for index, row in df.iterrows():
            # Handle semester rows
            if pd.notna(row['Semester']):
                current_semester = self.parse_semester(row['Semester'])
                self.stdout.write(f"\n=== Semester {current_semester} ===")
                current_section = None
                continue

            # Handle section headers (ONLY known ones)
            section_cell = row['Unnamed: 1']
            if pd.notna(section_cell):
                clean_section = str(section_cell).strip()
                if clean_section in self.section_headers:
                    current_section = clean_section
                    self.stdout.write(f"\nSection: {current_section}")
                    continue  # Skip section header row

            # Process subject rows
            code = str(row['Unnamed: 1']).strip() if pd.notna(row['Unnamed: 1']) else ''
            name = str(row['Unnamed: 2']).strip() if pd.notna(row['Unnamed: 2']) else ''

            # Skip empty/invalid rows
            if not code or not name:
                continue
            if code in self.section_headers:
                continue

            # Classification
            is_elective = any(x in code for x in ['PEC', 'OEC', 'PE', 'OE']) 
            stream = self.get_stream(code, name, current_section)

            # Create record
            if current_semester:
                Subject.objects.update_or_create(
                    code=code,
                    semester=current_semester,
                    defaults={
                        'name': name,
                        'stream': stream,
                        'is_elective': is_elective
                    }
                )
                self.stdout.write(f"  ✅ Imported: {code} | {name[:25]}...")

    def parse_semester(self, text):
        sem_map = {
            '1st': 1, '2nd': 2, '3rd': 3, '4th': 4,
            '5th': 5, '6th': 6, '7th': 7, '8th': 8,
            'Seventh': 7
        }
        text = str(text).replace('Semster', 'Semester')
        for term, num in sem_map.items():
            if term in text:
                return num
        return None

    def get_stream(self, code, name, current_section):
        if 'Lab' in name or 'Practical' in name:
            return 'Laboratory'
        if 'Project' in name:
            return 'Project'
        if 'BS-' in code:
            return 'Basic Science'
        if 'HSMC' in code:
            return 'Humanities'
        if current_section and 'Elective' in current_section:
            return 'Professional Elective' if 'PE' in code else 'Open Elective'
        return 'Core CS'