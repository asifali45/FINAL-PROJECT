import os
import logging
import json
import pandas as pd
from datetime import datetime
from flask import render_template, url_for, flash, redirect, request, jsonify, current_app, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from flask_wtf.csrf import generate_csrf
from app import app, db
from models import User, ExtractedForm
from forms import LoginForm, RegistrationForm, TemplateSelectionForm, FormUploadForm
from gemini_form_extractor import GeminiFormExtractor
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
    
    if form.validate_on_submit():
        # Save the uploaded file temporarily
        uploaded_file = form.form_file.data
        temp_dir = tempfile.mkdtemp()
        filename = secure_filename(uploaded_file.filename)
        temp_path = os.path.join(temp_dir, filename)
        uploaded_file.save(temp_path)
        
        try:
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
            os.rmdir(temp_dir)
    
    return render_template('form_upload.html', title='Upload Form', form=form, template=selected_template)

@app.route('/review-data', methods=['GET', 'POST'])
@login_required
def review_data():
    # Check if extracted data is available in session
    if 'extracted_data' not in session or 'selected_template' not in session:
        flash('No extracted data to review. Please upload a form first.', 'warning')
        return redirect(url_for('template_selection'))
    
    if request.method == 'POST':
        # Get the updated form data from the submitted form
        updated_data = {}
        
        for section, fields in session['extracted_data'].items():
            section_data = {}
            # Check if fields is a dictionary (from Gemini API)
            if isinstance(fields, dict):
                for field, value in fields.items():
                    field_id = f"{section}_{field}".replace(" ", "_").replace("'", "")
                    field_value = request.form.get(field_id, "")
                    section_data[field] = field_value
            else:
                # Backward compatibility with old format
                for field in fields:
                    field_id = f"{section}_{field}".replace(" ", "_").replace("'", "")
                    field_value = request.form.get(field_id, "")
                    section_data[field] = field_value
            
            updated_data[section] = section_data
        
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
    
    return render_template(
        'review_data.html', 
        title='Review Data', 
        template_type=session['selected_template'],
        extracted_data=session['extracted_data']
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
    logger.debug(f"Form data retrieved: {form_data}")
    
    # Ensure all sections are dictionaries for consistency
    # (Convert any list-based field structures to dictionaries)
    for section, fields in form_data.items():
        if not isinstance(fields, dict):
            # If we have a list of fields, convert to empty dictionary
            form_data[section] = {field: "" for field in fields}
    
    return render_template(
        'review_data.html', 
        title='View Form', 
        template_type=extracted_form.template_type,
        extracted_data=form_data,
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
    # (Convert any list-based field structures to dictionaries)
    for section, fields in form_data.items():
        if not isinstance(fields, dict):
            # If we have a list of fields, convert to empty dictionary
            form_data[section] = {field: "" for field in fields}
    
    # Return the data to be handled by client-side export functions
    if format == 'json':
        # For Excel export, we'll use json as an intermediate
        data = {
            'formId': form_id,
            'templateType': template_type,
            'fileName': extracted_form.file_name,
            'extractedData': form_data
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
