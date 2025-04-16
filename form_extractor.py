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
        self.logger = logging.getLogger(__name__)
        
        # Validate endpoint
        if not endpoint or not isinstance(endpoint, str):
            self.logger.error(f"Invalid endpoint: {endpoint}")
            raise ValueError("Endpoint must be a valid URL string")
        
        # Validate API key
        if not api_key or not isinstance(api_key, str):
            self.logger.error("Invalid API key provided")
            raise ValueError("API key must be a valid string")
            
        self.logger.info(f"Initializing Form Recognizer client with endpoint: {endpoint}")
        self.logger.debug(f"API key length: {len(api_key)}")
        
        self.endpoint = endpoint
        self.api_key = api_key
        
        try:
            self.client = DocumentAnalysisClient(
                endpoint=endpoint, 
                credential=AzureKeyCredential(api_key)
            )
            self.logger.info("Form Recognizer client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Form Recognizer client: {str(e)}")
            raise
    
    def extract_form_data(self, file_path, template_type):
        """
        Extract data from a form using Azure Form Recognizer
        
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
            # Read the form file
            with open(file_path, "rb") as f:
                form_bytes = f.read()
                
            self.logger.info(f"File read successfully, size: {len(form_bytes)} bytes")
            
            # Use a mock extraction for testing if needed
            if os.environ.get('USE_MOCK_EXTRACTION') == 'true':
                self.logger.warning("Using mock extraction instead of Azure Form Recognizer")
                # Create a mock extracted text with some sample data
                extracted_text = self._get_mock_extracted_text(template_type)
            else:
                # Analyze the document using Azure Form Recognizer
                self.logger.info("Sending document to Azure Form Recognizer for analysis")
                poller = self.client.begin_analyze_document("prebuilt-document", form_bytes)
                self.logger.info("Waiting for analysis to complete...")
                result = poller.result()
                self.logger.info("Analysis completed successfully")
                
                # Check if any pages were found
                if not result.pages or len(result.pages) == 0:
                    self.logger.error("No pages found in the document")
                    raise ValueError("No pages found in the document")
                
                # Extract text from the document
                extracted_text = " ".join([p.content for p in result.pages[0].lines])
                self.logger.info(f"Extracted text length: {len(extracted_text)} characters")
                
            # Map the extracted text to form fields using regex patterns
            self.logger.info("Mapping extracted text to form fields")
            mapped_data = self._map_extracted_text_to_fields(extracted_text, template_type)
            self.logger.info("Mapping completed successfully")
            
            return mapped_data
            
        except Exception as e:
            self.logger.error(f"Error extracting form data: {str(e)}")
            raise
    
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
