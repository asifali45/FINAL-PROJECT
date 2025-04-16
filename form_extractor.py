import os
import re
import logging
import tempfile
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from form_templates import FORM_TEMPLATES

class FormExtractor:
    def __init__(self, endpoint, api_key):
        """
        Initialize the Azure Form Recognizer client
        
        Args:
            endpoint (str): Azure Form Recognizer endpoint
            api_key (str): Azure Form Recognizer API key
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.client = DocumentAnalysisClient(
            endpoint=endpoint, 
            credential=AzureKeyCredential(api_key)
        )
        self.logger = logging.getLogger(__name__)
    
    def extract_form_data(self, file_path, template_type):
        """
        Extract data from a form using Azure Form Recognizer
        
        Args:
            file_path (str): Path to the uploaded form file
            template_type (str): Type of form template (Biodata, Admission, Bank Account)
            
        Returns:
            dict: Extracted and mapped form data organized by sections
        """
        try:
            # Read the form file
            with open(file_path, "rb") as f:
                form_bytes = f.read()
            
            # Analyze the document using Azure Form Recognizer
            poller = self.client.begin_analyze_document("prebuilt-document", form_bytes)
            result = poller.result()
            
            # Extract text from the document
            extracted_text = " ".join([p.content for p in result.pages[0].lines])
            self.logger.debug(f"Extracted text: {extracted_text}")
            
            # Map the extracted text to form fields using regex patterns
            return self._map_extracted_text_to_fields(extracted_text, template_type)
            
        except Exception as e:
            self.logger.error(f"Error extracting form data: {str(e)}")
            raise e
    
    def _map_extracted_text_to_fields(self, extracted_text, template_type):
        """
        Map extracted text to form fields using regex patterns
        
        Args:
            extracted_text (str): Extracted text from the form
            template_type (str): Type of form template
            
        Returns:
            dict: Mapped form data organized by sections
        """
        mapped_data = {}
        
        # Get the template for the selected form type
        template = FORM_TEMPLATES.get(template_type)
        if not template:
            raise ValueError(f"Invalid template type: {template_type}")
        
        # Process each section in the template
        for section_name, fields in template.items():
            section_data = {}
            
            # Process each field in the section
            for field_info in fields:
                field_name = field_info["field"]
                regex_pattern = field_info["regex"]
                
                # Try to match the field in the extracted text
                match = re.search(regex_pattern, extracted_text)
                if match and match.group(1):
                    field_value = match.group(1).strip()
                else:
                    field_value = ""
                
                section_data[field_name] = field_value
            
            mapped_data[section_name] = section_data
        
        return mapped_data
