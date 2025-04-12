from flask import Flask, request, render_template
import os
import pandas as pd
import re

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Mapping subject codes to subject names and categories
SUBJECTS = {
    "PEC-IT801B": "Cryptography & Network Security",
    "PEC-IT801C": "Natural Language Processing",
    "OEC-IT801D": "Bio Informatics",
    "OEC-IT802A": "E-Commerce & ERP",
    "OEC-IT802C": "Economic Policies in India",
    "PEC-IT601B": "Distributed Systems",
    "PEC-IT601D": "Image Processing",
    "PEC-IT602B": "Data Warehousing & Data Mining",
    "PEC-IT602D": "Pattern Recognition",
    "OEC-IT601B": "HRD & Organizational Behaviour",
    "OEC-IT601A": "Numerical Methods",
}

CATEGORY_MAP = {
    "PEC-IT801B": "Professional Elective VI",
    "PEC-IT801C": "Professional Elective VI",
    "OEC-IT801D": "Open Elective III",
    "OEC-IT802A": "Open Elective IV",
    "OEC-IT802C": "Open Elective IV",
    "PEC-IT601B": "Professional Elective VI",
    "PEC-IT601D": "Professional Elective VI",
    "PEC-IT602B": "Professional Elective VII",
    "PEC-IT602D": "Professional Elective VII",
    "OEC-IT601B": "Open Elective III",
    "OEC-IT601A": "Open Elective III",
}

# === Helper Functions ===

def normalize_code(code):
    """Convert raw subject code to standardized format like 'PEC-IT801B'."""
    if pd.isna(code) or not isinstance(code, str) or not code.strip():
        return None
    code = code.strip().strip("'")
    if "-" not in code and len(code) >= 7 and code.isalnum():
        return f"{code[:3]}-{code[3:]}"
    return code

def extract_electives(subjects_str, subjects_dict):
    """Extract and normalize all valid elective codes from raw enrollment string."""
    if pd.isna(subjects_str) or not isinstance(subjects_str, str) or not subjects_str.strip():
        return []
    parts = re.findall(r"'([^']*)'|([^,]+)", subjects_str)
    all_parts = [p[0] if p[0] else p[1] for p in parts if p[0] or p[1]]
    return [normalize_code(p.strip()) for p in all_parts if normalize_code(p.strip()) in subjects_dict]

def process_and_compare(enroll_file, alloc_file):
    try:
        # Read enrollment data
        df_enroll = pd.read_excel(enroll_file)
        df_enroll["ROLL NO"] = df_enroll["ROLL NO"].astype(str).str.replace('.0', '').str.strip()
        df_enroll.set_index("ROLL NO", inplace=True)

        # Read allocation data with multi-index header
        df_alloc = pd.read_excel(alloc_file, header=[0, 1])
        roll_no_col = next(col for col in df_alloc.columns if "roll no" in col[0].lower())
        df_alloc[roll_no_col] = df_alloc[roll_no_col].astype(str).str.replace('.0', '').str.strip()
        df_alloc.set_index(roll_no_col, inplace=True)

        # Define elective categories
        elective_categories = sorted([col for col in df_alloc.columns.levels[0] if "Elective" in col])

        # Map codes to categories from allocation data
        category_to_codes = {}
        for category in elective_categories:
            codes = [normalize_code(subcol[1].split('(')[-1].replace(')', '').replace(' ', '')) 
                     for subcol in df_alloc[category].columns 
                     if '(' in subcol[1]]
            category_to_codes[category] = codes

        results = []
        for roll_no in df_enroll.index:
            subjects_str = df_enroll.loc[roll_no, "Subjects"]
            chosen_electives = extract_electives(subjects_str, SUBJECTS)

            # If no chosen electives from enrollment, use allocation data as fallback
            if not chosen_electives and roll_no in df_alloc.index:
                chosen_electives = []
                row = df_alloc.loc[roll_no]
                for category in elective_categories:
                    chosen_code = next((normalize_code(row[category, subcol]) 
                                      for subcol in df_alloc[category].columns 
                                      if pd.notna(row[category, subcol]) and normalize_code(row[category, subcol]) in SUBJECTS), None)
                    if chosen_code:
                        chosen_electives.append(chosen_code)

            all_chosen_bullets = "\n" + "\n".join([f"- {SUBJECTS[code]} ({code})" for code in chosen_electives]) if chosen_electives else ""

            # Map chosen electives to their categories
            chosen_by_category = {CATEGORY_MAP.get(code): code for code in chosen_electives if code in CATEGORY_MAP}

            # Extract allocated electives
            allocated = {}
            if roll_no in df_alloc.index:
                row = df_alloc.loc[roll_no]
                for category in elective_categories:
                    allocated_code = next((normalize_code(row[category, subcol]) 
                                        for subcol in df_alloc[category].columns 
                                        if pd.notna(row[category, subcol]) and normalize_code(row[category, subcol]) in SUBJECTS), None)
                    allocated[category] = allocated_code
            else:
                allocated = {cat: None for cat in elective_categories}

            # Build results for this roll number
            for i, category in enumerate(elective_categories):
                chosen_code = chosen_by_category.get(category)
                allocated_code = allocated.get(category)

                # Use allocation data as chosen if no enrollment choice exists
                if not chosen_code and allocated_code:
                    chosen_code = allocated_code

                if not chosen_code and not allocated_code:
                    status = "Not Chosen/Not Allocated"
                elif not chosen_code:
                    status = "Not Chosen"
                elif not allocated_code:
                    status = "Pending Allocation"
                else:
                    status = "Match" if chosen_code == allocated_code else "Mismatch"

                # For "Pending Allocation", show the chosen subject; otherwise, handle as before
                if status == "Pending Allocation":
                    chosen_display = f"{SUBJECTS.get(chosen_code)} ({chosen_code})"
                else:
                    chosen_display = (f"{SUBJECTS.get(chosen_code)} ({chosen_code})" if chosen_code 
                                    else f"None{all_chosen_bullets}" if all_chosen_bullets else "None")
                
                allocated_display = (f"{SUBJECTS.get(allocated_code)} ({allocated_code})" 
                                   if allocated_code else "Not Allocated")

                results.append({
                    "Roll No": roll_no if i == 0 else "",  # Only show Roll No on first row
                    "Elective Category": category,
                    "Chosen": chosen_display,
                    "Allocated": allocated_display,
                    "Status": status,
                    "rowspan": 3 if i == 0 else 0  # Set rowspan for Roll No
                })

        return results

    except Exception as e:
        raise Exception(f"Error processing files: {str(e)}")

# === Flask Routes ===

@app.route('/', methods=['GET', 'POST'])
def upload_files():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    if request.method == 'POST':
        file1 = request.files.get('file1')
        file2 = request.files.get('file2')

        if file1 and file2:
            path1 = os.path.join(app.config['UPLOAD_FOLDER'], 'enrollment.xlsx')
            path2 = os.path.join(app.config['UPLOAD_FOLDER'], 'allocation.xlsx')
            file1.save(path1)
            file2.save(path2)

            try:
                results = process_and_compare(path1, path2)
                return render_template('results.html', results=results)
            except Exception as e:
                return f"<h4>Error occurred:</h4><pre>{str(e)}</pre>", 500

    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)