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
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

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
    
    # Get the form data
    form_data = extracted_form.get_data()
    template_type = extracted_form.template_type
    
    # Ensure all sections are dictionaries for consistency
    # Add missing fields from template if not present
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
    
    # Return the data to be handled by client-side export functions
    if format == 'json':
        # For Excel export, we'll use json as an intermediate
        data = {
            'formId': form_id,
            'templateType': template_type,
            'fileName': extracted_form.file_name,
            'extractedData': complete_form_data
        }
        return jsonify(data)
    else:
        flash('Invalid export format.', 'danger')
        return redirect(url_for('view_form', form_id=form_id))

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
