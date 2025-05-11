import pandas as pd
import os
import re
from django.conf import settings
from django.core.management.base import BaseCommand
from core.models import Subject

class Command(BaseCommand):
    help = 'Import subjects with semester-wise core subjects and elective groups'

    def handle(self, *args, **kwargs):
        files = [
            (os.path.join(settings.BASE_DIR, 'SubjectData', 'Odd_Semesters.xlsx'), 'ODD'),
            (os.path.join(settings.BASE_DIR, 'SubjectData', 'Subject List even.xlsx'), 'EVEN')
        ]

        initial_count = Subject.objects.count()
        self.stdout.write(f"Initial subject count: {initial_count}")

        for file_path, sem_type in files:
            self.stdout.write(f"\n{'#'*40}\nChecking file: {file_path}\n{'#'*40}")
            if not os.path.exists(file_path):
                self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
                continue

            try:
                df = pd.read_excel(file_path, sheet_name='Sheet1', header=0)
                self.stdout.write(f"Loaded {len(df)} rows from {os.path.basename(file_path)}")
                self.process_file(df, sem_type)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {file_path}: {str(e)}"))

        final_count = Subject.objects.count()
        self.stdout.write(f"\nFinal subject count: {final_count}")
        self.stdout.write(f"Subjects added: {final_count - initial_count}")

    def process_file(self, df, sem_type):
        current_semester = None
        current_section = None
        current_elective_group = None
        pe_group_counter = {}  # Tracks PE groups within each elective section

        for index, row in df.iterrows():
            semester_value = row.get('Semester')
            code_cell = row.get('Unnamed: 1')
            name_cell = row.get('Unnamed: 2')

            # Detect semester changes
            if pd.notna(semester_value):
                current_semester = self.parse_semester(str(semester_value))
                if current_semester is None:
                    self.stdout.write(self.style.WARNING(f"Invalid semester value: {semester_value}"))
                    continue
                self.stdout.write(f"\n=== Semester {current_semester} ===")
                current_section = None
                current_elective_group = None
                pe_group_counter = {}
                continue

            # Detect section headers (e.g., "Theory", "Laboratory", "Electives")
            if pd.notna(code_cell) and pd.isna(name_cell):
                current_section = str(code_cell).strip()
                self.stdout.write(f"Detected section header: {current_section}")
                current_elective_group = None
                if self.is_elective_section(current_section):
                    current_elective_group = self.parse_elective_group(current_section)
                    self.stdout.write(f"Elective Group: {current_elective_group}")
                continue

            # Process subject rows (both code and name are not NaN)
            if pd.notna(code_cell) and pd.notna(name_cell):
                code = str(code_cell).strip()
                name = str(name_cell).strip()
                if not code or not name:
                    self.stdout.write(self.style.WARNING(f"Skipping row {index + 2}: Invalid code or name"))
                    continue

                # Determine if it's an elective based on current section
                is_elective = bool(current_elective_group)
                stream = (
                    self.determine_elective_stream(code, current_elective_group, pe_group_counter)
                    if is_elective
                    else self.determine_core_stream(code, name, current_section)
                )

                # Create/update record
                try:
                    Subject.objects.update_or_create(
                        code=code,
                        semester=current_semester,
                        defaults={
                            'name': name,
                            'stream': stream,
                            'is_elective': is_elective
                        }
                    )
                    self.stdout.write(f"  ✅ {code}: {name[:30]}... | {stream}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error saving {code}: {str(e)}"))

    def parse_semester(self, text):
        text = text.lower()
        if '1st' in text: return 1
        elif '2nd' in text: return 2
        elif '3rd' in text: return 3
        elif '4th' in text: return 4
        elif '5th' in text: return 5
        elif '6th' in text: return 6
        elif '7th' in text or 'seventh' in text: return 7
        elif '8th' in text: return 8
        return None

    def is_elective_section(self, section_header):
        header = section_header.lower()
        return 'elective' in header or 'pe' in header or 'oe' in header or 'prof.' in header

    def parse_elective_group(self, section_header):
        header = section_header.strip().lower()
        match = re.search(r'(pe|oe|prof\.?|open)\s*(i{1,3}|iv|v|vi|\d+)', header)
        if match:
            group_type = 'PE' if 'pe' in match.group(1) or 'prof' in match.group(1) else 'OE'
            group_num = match.group(2).upper()
            return f"{group_type} {group_num}"
        return "Elective"

    def determine_elective_stream(self, code, elective_group, pe_group_counter):
        code = code.lower()
        if elective_group.startswith("OE"):
            return elective_group
        elif elective_group.startswith("PE"):
            pe_group_match = re.search(r'pec-it(\d{3})[a-z]', code)
            if pe_group_match:
                group_num = pe_group_match.group(1)
                if group_num not in pe_group_counter:
                    group_index = len(pe_group_counter) + 1
                    pe_group_counter[group_num] = f"{elective_group}"
                return pe_group_counter[group_num]
            return elective_group
        return elective_group

    def determine_core_stream(self, code, name, section):
        code = code.lower()
        name = name.lower()
        if 'lab' in name or 'laboratory' in name:
            return 'Laboratory'
        if 'practical' in name:
            return 'Practical'
        if 'project' in name:
            return 'Project'
        if 'bs-' in code:
            return 'Basic Science'
        if 'hsmc' in code:
            return 'Humanities'
        if 'cs' in code or 'it' in code:
            return 'Core CS'
        return section  # Fallback to section header (e.g., "Theory")