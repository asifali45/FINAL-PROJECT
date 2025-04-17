import os
import logging
import json
import base64
from datetime import datetime
from flask import render_template, url_for, flash, redirect, request, jsonify, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from flask_wtf.csrf import generate_csrf
from app import app, db
from models import User, ExtractedForm
from forms import LoginForm, RegistrationForm, TemplateSelectionForm, FormUploadForm
from gemini_form_extractor import GeminiFormExtractor
from form_templates import FORM_TEMPLATES
import tempfile

# Set up logging
logger = logging.getLogger(__name__)

# CSRF token context processor
@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf())

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
        
        login_user(user, remember=form.remember_me.data)
        flash('Login successful!', 'success')
        
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard')
        return redirect(next_page)
    
    return render_template('login.html', title='Sign In', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', title='Register', form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get all the user's extracted forms, ordered by newest first
    extracted_forms = ExtractedForm.query.filter_by(user_id=current_user.id).order_by(ExtractedForm.created_at.desc()).all()
    return render_template('dashboard.html', title='Dashboard', extracted_forms=extracted_forms)

@app.route('/template-selection', methods=['GET', 'POST'])
@login_required
def template_selection():
    form = TemplateSelectionForm()
    if form.validate_on_submit():
        # Store the selected template in the session
        session['selected_template'] = form.template.data
        return redirect(url_for('form_upload'))
    
    return render_template('template_selection.html', title='Select Template', form=form)

@app.route('/form-upload', methods=['GET', 'POST'])
@login_required
def form_upload():
    # Check if template was selected
    if 'selected_template' not in session:
        flash('Please select a template first', 'warning')
        return redirect(url_for('template_selection'))
    
    selected_template = session['selected_template']
    form = FormUploadForm()
    
    if form.validate_on_submit() or 'camera_image' in request.form:
        temp_dir = tempfile.mkdtemp()
        temp_path = ""
        filename = ""
        
        try:
            # Check if we received camera data or file upload
            if 'camera_image' in request.form and request.form['camera_image']:
                # Handle camera image (base64 encoded)
                camera_data = request.form['camera_image']
                
                # Remove the data URL prefix if present (e.g., "data:image/jpeg;base64,")
                if ',' in camera_data:
                    camera_data = camera_data.split(',', 1)[1]
                
                # Decode base64 data
                image_data = base64.b64decode(camera_data)
                
                # Save to temp file
                filename = f"camera_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                temp_path = os.path.join(temp_dir, filename)
                
                with open(temp_path, 'wb') as f:
                    f.write(image_data)
                
                logger.debug(f"Saved camera capture to {temp_path}")
                
            elif form.form_file.data:
                # Handle regular file upload
                uploaded_file = form.form_file.data
                filename = secure_filename(uploaded_file.filename)
                temp_path = os.path.join(temp_dir, filename)
                uploaded_file.save(temp_path)
                logger.debug(f"Saved uploaded file to {temp_path}")
            else:
                flash('No file or camera image provided', 'danger')
                return render_template('form_upload.html', title='Upload Form', form=form, template=selected_template)
            
            # Extract data using Google Gemini API
            api_key = app.config['GOOGLE_API_KEY']
            
            logger.debug(f"Using Google Gemini API for extraction")
            logger.debug(f"API key length: {len(api_key) if api_key else 0}")
            
            extractor = GeminiFormExtractor(api_key=api_key)
            
            extracted_data = extractor.extract_form_data(temp_path, selected_template)
            
            # Store extracted data in session to be used in review page
            session['extracted_data'] = extracted_data
            session['uploaded_filename'] = filename
            
            flash('Form data extracted successfully!', 'success')
            return redirect(url_for('review_data'))
            
        except Exception as e:
            logger.error(f"Error extracting form data: {str(e)}")
            flash(f'Error extracting form data: {str(e)}', 'danger')
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
    
    return render_template('form_upload.html', title='Upload Form', form=form, template=selected_template)

@app.route('/review-data', methods=['GET', 'POST'])
@login_required
def review_data():
    # Check if extracted data is available in session
    if 'extracted_data' not in session or 'selected_template' not in session:
        flash('No extracted data to review. Please upload a form first.', 'warning')
        return redirect(url_for('template_selection'))
    
    # Get the template structure for the selected template
    template_type = session['selected_template']
    template = FORM_TEMPLATES.get(template_type, {})
    
    if request.method == 'POST':
        # Debug: Log all form data received
        logger.debug("FORM DATA RECEIVED:")
        for key, value in request.form.items():
            logger.debug(f"  {key}: {value}")
            
        # Get the updated form data from the submitted form
        updated_data = {}
        
        # Process form data based on the template structure
        for section_name, fields_info in template.items():
            section_data = {}
            
            # Go through each field in this section template
            for field_info in fields_info:
                field_name = field_info["field"]
                
                # Match the field ID format used in the template
                # In the template: {{ section }}_{{ field|replace(' ', '_')|replace("'", "") }}
                field_id = f"{section_name}_{field_name}".replace(" ", "_").replace("'", "")
                
                # Try both formats - with and without space replacement
                field_value = request.form.get(field_id, "")
                
                # If empty, try with spaces (as seen in the form submission)
                if not field_value:
                    alternate_field_id = f"{section_name} {field_name}"
                    field_value = request.form.get(alternate_field_id, "")
                    if field_value:
                        logger.debug(f"Found value using alternate ID: {alternate_field_id}")
                
                # Debug this specific field
                logger.debug(f"Field: {field_id}, Value from form: '{field_value}'")
                
                # Store the form value 
                section_data[field_name] = field_value
                
            updated_data[section_name] = section_data
            
        # Log data before saving
        logger.debug(f"Saving updated form data: {updated_data}")
        
        # Save the extracted form data to the database
        extracted_form = ExtractedForm(
            user_id=current_user.id,
            template_type=session['selected_template'],
            file_name=session['uploaded_filename']
        )
        extracted_form.set_data(updated_data)
        
        db.session.add(extracted_form)
        db.session.commit()
        
        # Clear the session data
        session.pop('extracted_data', None)
        session.pop('selected_template', None)
        session.pop('uploaded_filename', None)
        
        flash('Form data saved successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    # For GET requests, pass the template data to the template
    extracted_data = session['extracted_data']
    logger.debug(f"Displaying data for review: {extracted_data}")
    
    return render_template(
        'review_data.html', 
        title='Review Data', 
        template_type=session['selected_template'],
        extracted_data=extracted_data
    )

@app.route('/view-form/<int:form_id>')
@login_required
def view_form(form_id):
    # Get the form data from the database
    extracted_form = ExtractedForm.query.get_or_404(form_id)
    
    # Check if the form belongs to the current user
    if extracted_form.user_id != current_user.id:
        flash('You do not have permission to view this form.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get form data and ensure it's in the proper format for the template
    form_data = extracted_form.get_data()
    
    # Log form data for debugging
    logger.debug(f"Original form data retrieved: {form_data}")
    
    # Ensure all sections are dictionaries for consistency
    # Add missing fields from template if not present
    template_type = extracted_form.template_type
    template = FORM_TEMPLATES.get(template_type, {})
    
    # Create a complete form structure with empty values if fields are missing
    complete_form_data = {}
    
    for section_name, fields_info in template.items():
        section_data = {}
        # Initialize with empty data for all fields from template
        for field_info in fields_info:
            field_name = field_info["field"]
            section_data[field_name] = ""
            
        # If section exists in saved data, use those values
        if section_name in form_data and isinstance(form_data[section_name], dict):
            for field_name, value in form_data[section_name].items():
                section_data[field_name] = value
                
        complete_form_data[section_name] = section_data
    
    logger.debug(f"Complete form data with template fields: {complete_form_data}")
    
    return render_template(
        'review_data.html', 
        title='View Form', 
        template_type=extracted_form.template_type,
        extracted_data=complete_form_data,
        view_only=True,
        form_id=form_id
    )

@app.route('/export-form/<int:form_id>/<format>')
@login_required
def export_form(form_id, format):
    # Get the form data from the database
    extracted_form = ExtractedForm.query.get_or_404(form_id)
    
    # Check if the form belongs to the current user
    if extracted_form.user_id != current_user.id:
        flash('You do not have permission to export this form.', 'danger')
        return redirect(url_for('dashboard'))
    
    # For debugging: Print raw data from database
    raw_data = extracted_form.extracted_data
    logger.debug(f"Raw data from DB: {raw_data}")
    
    # Get the form data
    form_data = extracted_form.get_data()
    logger.debug(f"Parsed JSON data: {form_data}")
    
    template_type = extracted_form.template_type
    logger.debug(f"Template type: {template_type}")
    
    # Ensure all sections are dictionaries for consistency
    # Add missing fields from template if not present
    template = FORM_TEMPLATES.get(template_type, {})
    
    # Create a complete form structure with empty values if fields are missing
    complete_form_data = {}
    
    # Debug: Log template structure
    logger.debug(f"Template structure: {template.keys()}")
    
    for section_name, fields_info in template.items():
        section_data = {}
        logger.debug(f"Processing section: {section_name} with {len(fields_info)} fields")
        
        # Initialize with empty data for all fields from template
        for field_info in fields_info:
            field_name = field_info["field"]
            section_data[field_name] = ""
            logger.debug(f"Initialized field: {field_name}")
            
        # If section exists in saved data, use those values
        if section_name in form_data and isinstance(form_data[section_name], dict):
            logger.debug(f"Found section {section_name} in form data with {len(form_data[section_name])} fields")
            for field_name, value in form_data[section_name].items():
                section_data[field_name] = value
                logger.debug(f"Set field {field_name} = '{value}'")
        else:
            logger.debug(f"Section {section_name} not found in form data or not a dictionary")
                
        complete_form_data[section_name] = section_data
    
    # Final debug: Log complete data being sent
    logger.debug(f"Complete data being sent: {complete_form_data}")
    
    # Return the data to be handled by client-side export functions
    if format == 'json':
        # For Excel export, we'll use json as an intermediate
        data = {
            'formId': form_id,
            'templateType': template_type,
            'fileName': extracted_form.file_name,
            'extractedData': complete_form_data
        }
        logger.debug(f"JSON response keys: {data.keys()}")
        logger.debug(f"JSON extractedData sections: {data['extractedData'].keys()}")
        logger.debug(f"Sample data from first section: {list(data['extractedData'].values())[0] if data['extractedData'] else 'No data'}")
        
        return jsonify(data)
    elif format == 'excel':
        # Server-side Excel generation
        import pandas as pd
        import io
        from flask import send_file
        
        # Create an in-memory output file
        output = io.BytesIO()
        
        # Create a Pandas Excel writer using the output buffer
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Create summary sheet
            summary_data = [
                [f"{template_type} Form"],
                ["Original File:", extracted_form.file_name],
                ["Export Date:", datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                [],
                ["Form Sections:"]
            ]
            
            # Add sections to summary
            for idx, section_name in enumerate(complete_form_data.keys()):
                summary_data.append([f"{idx + 1}. {section_name}"])
            
            # Create DataFrame for summary and write to sheet
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', header=False, index=False)
            
            # Create detailed sheets for each section
            for section_name, fields in complete_form_data.items():
                # Create data list for section with field-value pairs
                section_data = []
                section_data.append([section_name])
                section_data.append([])  # Empty row
                section_data.append(["Field", "Value"])
                
                for field, value in fields.items():
                    section_data.append([field, value or ''])
                
                # Create DataFrame and write to sheet
                section_df = pd.DataFrame(section_data)
                safe_section_name = section_name.replace('/', '-').replace('\\', '-')[:31]
                section_df.to_excel(writer, sheet_name=safe_section_name, header=False, index=False)
                
                # Also create a table view of the data
                fields_df = pd.DataFrame([fields])
                table_sheet_name = f"{safe_section_name}_Table"[:31]
                fields_df.to_excel(writer, sheet_name=table_sheet_name, index=False)
            
            # Create a consolidated "All Data" sheet with all section data
            all_data = []
            all_data.append(["Section", "Field", "Value"])
            
            for section, fields in complete_form_data.items():
                for field, value in fields.items():
                    all_data.append([section, field, value or ''])
            
            all_data_df = pd.DataFrame(all_data[1:], columns=all_data[0])
            all_data_df.to_excel(writer, sheet_name='All Data', index=False)
        
        # Set the file pointer at the beginning of the file
        output.seek(0)
        
        # Create a file name
        file_name = f"{template_type.replace(' ', '_')}_Form_{form_id}.xlsx"
        
        # Return the Excel file for download
        return send_file(
            output, 
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name=file_name,
            as_attachment=True
        )
    else:
        flash('Invalid export format.', 'danger')
        return redirect(url_for('view_form', form_id=form_id))

@app.route('/export-all-forms/<format>')
@login_required
def export_all_forms(format):
    """
    Export all forms for the current user, organized by template type
    """
    logger.debug("Starting export-all-forms")
    
    # Get all the user's extracted forms
    extracted_forms = ExtractedForm.query.filter_by(user_id=current_user.id).order_by(ExtractedForm.created_at.desc()).all()
    logger.debug(f"Found {len(extracted_forms)} forms to export")
    
    if not extracted_forms:
        flash('No forms to export.', 'warning')
        return redirect(url_for('dashboard'))
    
    # Group forms by template type
    forms_by_template = {}
    
    for form in extracted_forms:
        template_type = form.template_type
        logger.debug(f"Processing form ID: {form.id}, Template: {template_type}, File: {form.file_name}")
        
        # Initialize entry for this template type if it doesn't exist
        if template_type not in forms_by_template:
            forms_by_template[template_type] = []
            logger.debug(f"Created new template group: {template_type}")
            
        # Get raw form data for debugging
        raw_data = form.extracted_data
        logger.debug(f"Raw data from DB for form {form.id}: {raw_data[:100]}...")
            
        # Get form data
        form_data = form.get_data()
        logger.debug(f"Parsed JSON data for form {form.id}: {str(form_data)[:200]}...")
        
        # Ensure form data follows the template structure
        template = FORM_TEMPLATES.get(template_type, {})
        logger.debug(f"Template sections for {template_type}: {template.keys()}")
        
        complete_form_data = {}
        
        # Process each section
        for section_name, fields_info in template.items():
            section_data = {}
            logger.debug(f"Processing section: {section_name} with {len(fields_info)} fields")
            
            # Initialize with empty data for all fields from template
            for field_info in fields_info:
                field_name = field_info["field"]
                section_data[field_name] = ""
                
            # If section exists in saved data, use those values
            if section_name in form_data and isinstance(form_data[section_name], dict):
                logger.debug(f"Found section {section_name} in form data with {len(form_data[section_name])} fields")
                for field_name, value in form_data[section_name].items():
                    section_data[field_name] = value
                    logger.debug(f"Set field {field_name} = '{value}'")
            else:
                logger.debug(f"Section {section_name} not found in form data or not a dictionary")
                    
            complete_form_data[section_name] = section_data
            
        # Verify data is correctly populated
        logger.debug(f"Processed form {form.id} has {len(complete_form_data)} sections")
        for section, fields in complete_form_data.items():
            logger.debug(f"Section {section} has {len(fields)} fields")
            for field, value in fields.items():
                if value:  # Only log non-empty values to reduce log size
                    logger.debug(f"Field {field} = '{value}'")
            
        # Add form metadata
        form_info = {
            'formId': form.id,
            'fileName': form.file_name,
            'createdAt': form.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'extractedData': complete_form_data
        }
        
        # Add to the template group
        forms_by_template[template_type].append(form_info)
        logger.debug(f"Added form {form.id} to {template_type} group")
    
    # Return the data based on format
    if format == 'json':
        # For client-side Excel export, we'll still provide the JSON
        data = {
            'userId': current_user.id,
            'username': current_user.username,
            'exportDate': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'formsByTemplate': forms_by_template
        }
        
        # Final verification
        for template_type, forms in forms_by_template.items():
            logger.debug(f"Template {template_type} has {len(forms)} forms")
            # Log details of first form as a sample
            if forms:
                sample_form = forms[0]
                logger.debug(f"Sample form ID: {sample_form['formId']}")
                logger.debug(f"Sample form extracted_data sections: {sample_form['extractedData'].keys()}")
                # Log some field values from the first section
                sample_section = list(sample_form['extractedData'].keys())[0]
                logger.debug(f"Sample section {sample_section} data: {sample_form['extractedData'][sample_section]}")
        
        return jsonify(data)
    elif format == 'excel':
        # Server-side Excel generation for all forms
        import pandas as pd
        import io
        from flask import send_file
        
        # Create an in-memory output file
        output = io.BytesIO()
        
        # Create a Pandas Excel writer using the output buffer
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Create summary sheet
            summary_data = [
                ['FormOCR - All Forms Export'],
                ['User:', current_user.username],
                ['Export Date:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                [],
                ['Templates Included:']
            ]
            
            # Add template types to summary
            for idx, (template_type, forms) in enumerate(forms_by_template.items()):
                form_count = len(forms)
                summary_data.append([f"{idx + 1}. {template_type} ({form_count} forms)"])
            
            # Create DataFrame for summary and write to sheet
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', header=False, index=False)
            
            # Process each template type
            for template_type, forms in forms_by_template.items():
                if not forms:
                    continue  # Skip if no forms for this template
                
                # Create a summary sheet for this template type with form details
                template_summary_data = [
                    [f"{template_type} Forms Summary"],
                    [],
                    ['Form ID', 'File Name', 'Created Date']
                ]
                
                # Add each form to the summary
                for form in forms:
                    template_summary_data.append([form['formId'], form['fileName'], form['createdAt']])
                
                # Create DataFrame for template summary and write to sheet
                template_summary_df = pd.DataFrame(template_summary_data[2:], columns=template_summary_data[2])
                template_summary_df.to_excel(
                    writer, 
                    sheet_name=f"{template_type[:27]} Summary"[:31], 
                    header=True, 
                    index=False,
                    startrow=2
                )
                
                # Add title to the sheet
                worksheet = writer.sheets[f"{template_type[:27]} Summary"[:31]]
                worksheet.cell(row=1, column=1, value=template_summary_data[0][0])
                
                # For each section in the template, create a separate sheet with all forms
                template_structure = forms[0]['extractedData']
                for section_name in template_structure.keys():
                    # Get all fields for this section
                    all_fields = set()
                    for form in forms:
                        form_section = form['extractedData'].get(section_name, {})
                        all_fields.update(form_section.keys())
                    
                    # Create headers: basic form info + all fields
                    headers = ['Form ID', 'File Name', 'Created Date'] + sorted(list(all_fields))
                    
                    # Create rows for each form
                    rows = []
                    for form in forms:
                        row = [
                            form['formId'],
                            form['fileName'],
                            form['createdAt']
                        ]
                        
                        # Add values for each field
                        form_section = form['extractedData'].get(section_name, {})
                        for field in sorted(all_fields):
                            row.append(form_section.get(field, ''))
                        
                        rows.append(row)
                    
                    # Create DataFrame and write to sheet
                    section_df = pd.DataFrame(rows, columns=headers)
                    safe_template = template_type.replace('/', '-').replace('\\', '-')[:15]
                    safe_section = section_name.replace('/', '-').replace('\\', '-')[:15]
                    sheet_name = f"{safe_template}-{safe_section}"[:31]
                    section_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Create a detailed sheet with all forms' data for this template
                detailed_data = [
                    [f"{template_type} - All Forms Details"],
                    []
                ]
                
                # Add each form with all its data
                for form in forms:
                    detailed_data.append([f"Form ID: {form['formId']}", f"File: {form['fileName']}", f"Date: {form['createdAt']}"])
                    detailed_data.append([])
                    
                    # Add sections and fields
                    for section, fields in form['extractedData'].items():
                        detailed_data.append([section])
                        detailed_data.append(['Field', 'Value'])
                        
                        for field, value in fields.items():
                            detailed_data.append([field, value or ''])
                        
                        detailed_data.append([])  # Empty row after section
                    
                    detailed_data.append([])  # Extra empty row between forms
                
                # Create DataFrame and write to sheet
                detailed_df = pd.DataFrame(detailed_data)
                safe_template_name = template_type.replace('/', '-').replace('\\', '-')[:23]
                detailed_df.to_excel(
                    writer, 
                    sheet_name=f"{safe_template_name} Details"[:31],
                    header=False,
                    index=False
                )
                
                # Create a consolidated table with all fields from all sections
                all_fields_by_section = {}
                for section in template_structure.keys():
                    all_fields_by_section[section] = set()
                    for form in forms:
                        form_section = form['extractedData'].get(section, {})
                        all_fields_by_section[section].update(form_section.keys())
                
                # Create headers
                consol_headers = ['Form ID', 'File Name', 'Created Date']
                
                # Add section-field headers
                for section, fields in all_fields_by_section.items():
                    for field in sorted(fields):
                        consol_headers.append(f"{section} - {field}")
                
                # Create rows
                consol_rows = []
                for form in forms:
                    row = [
                        form['formId'],
                        form['fileName'],
                        form['createdAt']
                    ]
                    
                    # Add values for each section-field
                    for section, fields in all_fields_by_section.items():
                        form_section = form['extractedData'].get(section, {})
                        for field in sorted(fields):
                            row.append(form_section.get(field, ''))
                    
                    consol_rows.append(row)
                
                # Create DataFrame and write to sheet
                consol_df = pd.DataFrame(consol_rows, columns=consol_headers)
                safe_template_consol = template_type.replace('/', '-').replace('\\', '-')[:20]
                consol_df.to_excel(
                    writer, 
                    sheet_name=f"{safe_template_consol}"[:31],
                    index=False
                )
            
        # Reset the file pointer
        output.seek(0)
        
        # Create filename
        file_name = f"All_Forms_Export_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        
        # Return the Excel file for download
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name=file_name,
            as_attachment=True
        )
    else:
        flash('Invalid export format.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/view-saved-forms')
@login_required
def view_saved_forms():
    # Get all the user's extracted forms, ordered by newest first
    extracted_forms = ExtractedForm.query.filter_by(user_id=current_user.id).order_by(ExtractedForm.created_at.desc()).all()
    return render_template('view_saved_forms.html', title='Saved Forms', extracted_forms=extracted_forms)

@app.route('/delete-form/<int:form_id>', methods=['POST'])
@login_required
def delete_form(form_id):
    # Get the form data from the database
    extracted_form = ExtractedForm.query.get_or_404(form_id)
    
    # Check if the form belongs to the current user
    if extracted_form.user_id != current_user.id:
        flash('You do not have permission to delete this form.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Delete the form
    db.session.delete(extracted_form)
    db.session.commit()
    
    flash('Form deleted successfully!', 'success')
    return redirect(url_for('view_saved_forms'))
