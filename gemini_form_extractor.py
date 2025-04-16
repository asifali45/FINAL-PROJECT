import os
import re
import base64
import logging
import tempfile
from typing import Dict, Any

import google.generativeai as genai
from form_templates import FORM_TEMPLATES

class GeminiFormExtractor:
    def __init__(self, api_key):
        """
        Initialize the Gemini API client
        
        Args:
            api_key (str): Google Gemini API key
        """
        self.logger = logging.getLogger(__name__)
        
        # Validate API key
        if not api_key or not isinstance(api_key, str):
            self.logger.error("Invalid API key provided")
            raise ValueError("API key must be a valid string")
            
        self.logger.info("Initializing Gemini API client")
        self.api_key = api_key
        
        try:
            # Configure the Gemini API
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            self.logger.info("Gemini API client initialized successfully with gemini-1.5-flash model")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini API client: {str(e)}")
            raise
    
    def extract_form_data(self, file_path, template_type):
        """
        Extract data from a form using Google's Gemini API
        
        Args:
            file_path (str): Path to the uploaded form file
            template_type (str): Type of form template (Biodata, Admission, Bank Account)
            
        Returns:
            dict: Extracted and mapped form data organized by sections
        """
        if not os.path.exists(file_path):
            self.logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"The file {file_path} does not exist")
        
        # Validate template type
        if template_type not in FORM_TEMPLATES:
            self.logger.error(f"Invalid template type: {template_type}")
            raise ValueError(f"Invalid template type: {template_type}")
        
        self.logger.info(f"Extracting data from {file_path} using template: {template_type}")
        
        try:
            # Read the form file and encode as base64
            with open(file_path, "rb") as f:
                image_bytes = f.read()
                
            self.logger.info(f"File read successfully, size: {len(image_bytes)} bytes")
            
            # Get the fields we need to extract from the template
            template = FORM_TEMPLATES.get(template_type)
            fields_to_extract = self._get_fields_from_template(template)
            
            # Create a prompt that instructs Gemini to extract specific fields
            prompt = self._create_extraction_prompt(template_type, fields_to_extract)
            
            # Send the image to Gemini for analysis
            self.logger.info("Sending image to Gemini API for analysis")
            response = self._analyze_image_with_gemini(image_bytes, prompt)
            self.logger.info("Analysis completed successfully")
            
            # Parse the Gemini response and map to template fields
            extracted_data = self._parse_gemini_response(response, template_type)
            self.logger.info("Extraction completed successfully")
            
            return extracted_data
            
        except Exception as e:
            self.logger.error(f"Error extracting form data: {str(e)}")
            raise
    
    def _get_fields_from_template(self, template):
        """
        Extract all field names from the template structure
        
        Args:
            template (dict): Form template structure
            
        Returns:
            dict: Dictionary of section names and their fields
        """
        fields_dict = {}
        
        for section_name, fields in template.items():
            section_fields = []
            for field_info in fields:
                section_fields.append(field_info["field"])
            fields_dict[section_name] = section_fields
            
        return fields_dict
    
    def _create_extraction_prompt(self, template_type, fields_to_extract):
        """
        Create a prompt for Gemini to extract specific fields from the form
        
        Args:
            template_type (str): Type of form template
            fields_to_extract (dict): Dictionary of section names and their fields
            
        Returns:
            str: Prompt for Gemini
        """
        prompt = f"Extract information from this {template_type} form. "
        prompt += "For each of the following fields, provide the exact value as written in the form. "
        prompt += "If a field is not found, respond with 'NOT_FOUND' for that field.\n\n"
        
        for section, fields in fields_to_extract.items():
            prompt += f"Section: {section}\n"
            for field in fields:
                prompt += f"- {field}\n"
            prompt += "\n"
            
        prompt += "Format your response as JSON with sections as the top-level keys and field names as nested keys."
        prompt += "Example format: { 'Section Name': { 'Field Name': 'Value' } }"
        
        return prompt
    
    def _analyze_image_with_gemini(self, image_bytes, prompt):
        """
        Send the image to Gemini for analysis
        
        Args:
            image_bytes (bytes): Image file bytes
            prompt (str): Instruction prompt for Gemini
            
        Returns:
            str: Gemini's response
        """
        try:
            # Create the image parts for the Gemini API
            image_parts = [
                {
                    "mime_type": "image/jpeg",  # Assuming JPEG, adjust if needed
                    "data": base64.b64encode(image_bytes).decode('utf-8')
                }
            ]
            
            # Generate content with the image and prompt
            response = self.gemini_model.generate_content([prompt, *image_parts])
            
            # Extract the text response
            return response.text
            
        except Exception as e:
            self.logger.error(f"Error analyzing image with Gemini: {str(e)}")
            raise
    
    def _parse_gemini_response(self, response_text, template_type):
        """
        Parse the Gemini response and map to template structure
        
        Args:
            response_text (str): Response from Gemini API
            template_type (str): Type of form template
            
        Returns:
            dict: Extracted and mapped form data organized by sections
        """
        self.logger.info("Parsing Gemini response")
        self.logger.debug(f"Raw response: {response_text}")
        
        # Initialize the result with the template structure (empty values)
        template = FORM_TEMPLATES.get(template_type)
        result = {}
        
        for section_name, fields in template.items():
            section_data = {}
            for field_info in fields:
                field_name = field_info["field"]
                section_data[field_name] = ""
            result[section_name] = section_data
        
        try:
            # Try to extract JSON from the response
            import json
            import re
            
            # Look for JSON in the response
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                # If no JSON code block, try to find raw JSON
                json_match = re.search(r'({[\s\S]*})', response_text)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    self.logger.warning("Could not find JSON in Gemini response")
                    return result
            
            # Parse the JSON
            extracted_data = json.loads(json_str)
            
            # Map the extracted data to our template structure
            for section_name, fields in result.items():
                if section_name in extracted_data:
                    section_data = extracted_data[section_name]
                    for field_name in fields:
                        if field_name in section_data:
                            value = section_data[field_name]
                            # Don't use NOT_FOUND values
                            if value != "NOT_FOUND":
                                result[section_name][field_name] = value
            
        except Exception as e:
            self.logger.error(f"Error parsing Gemini response: {str(e)}")
            self.logger.debug(f"Response was: {response_text}")
            
            # Try regex fallback for key-value extraction
            self._extract_with_regex_fallback(response_text, result)
        
        return result
    
    def _extract_with_regex_fallback(self, response_text, result):
        """
        Fallback method to extract data using regex if JSON parsing fails
        
        Args:
            response_text (str): Response from Gemini API
            result (dict): Template structure to populate
            
        Returns:
            dict: Updated result dictionary
        """
        self.logger.info("Using regex fallback for extraction")
        
        # Look for patterns like "Field Name: Value" in the response
        for section_name, fields in result.items():
            for field_name in fields:
                # Create a pattern that looks for the field name followed by a value
                pattern = rf"{re.escape(field_name)}:\s*([^\n]+)"
                match = re.search(pattern, response_text)
                if match:
                    value = match.group(1).strip()
                    if value != "NOT_FOUND":
                        result[section_name][field_name] = value
                        
        return result