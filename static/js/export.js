// Export functionality for extracted forms

// Function to export form data as PDF
function exportToPDF(formId) {
    // Show loading spinner
    showSpinner();
    
    // Fetch the form data
    fetch(`/export-form/${formId}/json`)
        .then(response => response.json())
        .then(data => {
            const { templateType, fileName, extractedData } = data;
            
            // Create a new jsPDF instance
            const doc = new jspdf.jsPDF();
            
            // Set default font size and style
            doc.setFontSize(12);
            
            // Add title
            doc.setFontSize(18);
            doc.setFont(undefined, 'bold');
            doc.text(`${templateType} Form`, 105, 20, { align: 'center' });
            
            // Add file name and date
            doc.setFontSize(10);
            doc.setFont(undefined, 'normal');
            doc.text(`Original File: ${fileName}`, 105, 30, { align: 'center' });
            doc.text(`Exported on: ${new Date().toLocaleString()}`, 105, 35, { align: 'center' });
            
            // Add line separator
            doc.line(20, 40, 190, 40);
            
            // Set starting y position for form sections
            let yPos = 50;
            
            // Helper function to create a table
            function createTable(headers, rows, startY) {
                const margin = 20;
                const pageWidth = doc.internal.pageSize.width;
                const tableWidth = pageWidth - (margin * 2);
                const cellPadding = 5;
                const fontSize = 10;
                const lineHeight = 7;
                
                const columnWidth = tableWidth / headers.length;
                
                let y = startY;
                
                // Draw header
                doc.setFont(undefined, 'bold');
                doc.setFillColor(240, 240, 240);
                doc.rect(margin, y, tableWidth, lineHeight, 'F');
                
                headers.forEach((header, i) => {
                    doc.text(header, margin + (i * columnWidth) + cellPadding, y + (lineHeight * 0.7));
                });
                
                y += lineHeight;
                
                // Draw rows
                doc.setFont(undefined, 'normal');
                rows.forEach((row, rowIndex) => {
                    // Check if we need a new page
                    if (y > 270) {
                        doc.addPage();
                        y = 20;
                        
                        // Re-draw header on new page
                        doc.setFont(undefined, 'bold');
                        doc.setFillColor(240, 240, 240);
                        doc.rect(margin, y, tableWidth, lineHeight, 'F');
                        
                        headers.forEach((header, i) => {
                            doc.text(header, margin + (i * columnWidth) + cellPadding, y + (lineHeight * 0.7));
                        });
                        
                        y += lineHeight;
                        doc.setFont(undefined, 'normal');
                    }
                    
                    // Draw row background (alternating)
                    if (rowIndex % 2 === 1) {
                        doc.setFillColor(250, 250, 250);
                        doc.rect(margin, y, tableWidth, lineHeight, 'F');
                    }
                    
                    // Draw cell content
                    row.forEach((cell, i) => {
                        doc.text(String(cell), margin + (i * columnWidth) + cellPadding, y + (lineHeight * 0.7));
                    });
                    
                    y += lineHeight;
                });
                
                return y + 10; // Return the new Y position after the table
            }
            
            // Loop through each section in the extracted data
            for (const [section, fields] of Object.entries(extractedData)) {
                // Check if we need to add a new page for the section
                if (yPos > 260) {
                    doc.addPage();
                    yPos = 20;
                }
                
                // Add section header
                doc.setFont(undefined, 'bold');
                doc.setFontSize(14);
                doc.text(section, 20, yPos);
                yPos += 10;
                
                // Prepare table data
                const headers = ['Field', 'Value'];
                const rows = Object.entries(fields).map(([field, value]) => [field, value]);
                
                // Create table for this section
                yPos = createTable(headers, rows, yPos);
                
                // Add space between sections
                yPos += 5;
            }
            
            // Add footer with page numbers
            const pageCount = doc.internal.getNumberOfPages();
            for (let i = 1; i <= pageCount; i++) {
                doc.setPage(i);
                doc.setFontSize(10);
                doc.text(`Page ${i} of ${pageCount}`, 105, 287, { align: 'center' });
            }
            
            // Save the PDF
            doc.save(`${templateType.replace(' ', '_')}_Form_${formId}.pdf`);
            
            // Hide loading spinner
            hideSpinner();
        })
        .catch(error => {
            console.error('Error exporting to PDF:', error);
            alert('Error exporting to PDF. Please try again.');
            hideSpinner();
        });
}

// Function to export form data as Excel
function exportToExcel(formId) {
    // Show loading spinner
    showSpinner();
    
    console.log(`Starting export for form ID: ${formId}`);
    
    // Fetch the form data
    fetch(`/export-form/${formId}/json`)
        .then(response => {
            console.log('Response received:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Data received:', data);
            console.log('Data template type:', data.templateType);
            console.log('Data sections:', Object.keys(data.extractedData));
            console.log('First section data:', Object.values(data.extractedData)[0]);
            
            const { templateType, fileName, extractedData } = data;
            
            // Create a new workbook
            const wb = XLSX.utils.book_new();
            
            // No summary worksheet - removed as requested
            
            // Create a detailed data worksheet for each section
            Object.entries(extractedData).forEach(([section, fields]) => {
                // Create data for section
                const sectionData = [];
                
                // Add section header
                sectionData.push([`${section}`]);
                sectionData.push([]); // Empty row
                
                // Add field-value pairs
                Object.entries(fields).forEach(([field, value]) => {
                    sectionData.push([field, value || '']);
                });
                
                // Create and add section worksheet
                const sectionWs = XLSX.utils.aoa_to_sheet(sectionData);
                
                // Create a safe sheet name
                const safeSheetName = section.replace(/[\\/*[\]?]/g, '').substring(0, 31);
                XLSX.utils.book_append_sheet(wb, sectionWs, safeSheetName);
            });
            
            // Creating a data table for each section with field names in first row and values in second row
            Object.entries(extractedData).forEach(([section, fields]) => {
                // Create data table for section
                const tableData = [];
                
                // Get all field names as headers
                const headers = Object.keys(fields);
                tableData.push(headers);
                
                // Add values as a row
                const values = Object.values(fields).map(v => v || '');
                tableData.push(values);
                
                // Create and add table worksheet
                const tableWs = XLSX.utils.aoa_to_sheet(tableData);
                
                // Format the worksheet - adjust column widths
                const columnWidths = [];
                for (let i = 0; i < headers.length; i++) {
                    // Default width is max of 15 characters or header length
                    columnWidths[i] = { wch: Math.max(15, headers[i].length * 1.2) };
                }
                tableWs['!cols'] = columnWidths;
                
                // Create a safe sheet name
                const safeSheetName = `${section}_Table`.replace(/[\\/*[\]?]/g, '').substring(0, 31);
                XLSX.utils.book_append_sheet(wb, tableWs, safeSheetName);
            });
            
            // Create consolidated data worksheet for all sections combined
            const detailedData = [];
            detailedData.push(['Section', 'Field', 'Value']);
            
            // Add all sections and fields
            Object.entries(extractedData).forEach(([section, fields]) => {
                Object.entries(fields).forEach(([field, value]) => {
                    detailedData.push([section, field, value || '']);
                });
            });
            
            // Create and add all data worksheet
            const allDataWs = XLSX.utils.aoa_to_sheet(detailedData);
            
            // Format the worksheet - adjust column widths
            const allDataWidths = [
                { wch: 20 }, // Section column
                { wch: 25 }, // Field column
                { wch: 30 }  // Value column
            ];
            allDataWs['!cols'] = allDataWidths;
            
            XLSX.utils.book_append_sheet(wb, allDataWs, 'All Data');
            
            // Save workbook
            XLSX.writeFile(wb, `${templateType.replace(/\s+/g, '_')}_Form_${formId}.xlsx`);
            
            // Hide loading spinner
            hideSpinner();
        })
        .catch(error => {
            console.error('Error exporting to Excel:', error);
            alert('Error exporting to Excel. Please try again.');
            hideSpinner();
        });
}

// Function to export all user forms to a structured Excel workbook
function exportAllFormsToExcel() {
    // Show loading spinner
    showSpinner();
    
    console.log('Starting export for all forms');
    
    // Fetch all forms data
    fetch('/export-all-forms/json')
        .then(response => {
            console.log('Response received for all forms export:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('All forms data received');
            console.log('Templates available:', Object.keys(data.formsByTemplate));
            
            // Log first form of each template type as a sample
            for (const [templateType, forms] of Object.entries(data.formsByTemplate)) {
                if (forms.length > 0) {
                    console.log(`Sample form for template ${templateType}:`, forms[0]);
                    console.log(`Sample form sections:`, Object.keys(forms[0].extractedData));
                    
                    // Log one section's data as example
                    const sampleSection = Object.keys(forms[0].extractedData)[0];
                    console.log(`Sample section ${sampleSection} data:`, forms[0].extractedData[sampleSection]);
                }
            }
            
            const { username, exportDate, formsByTemplate } = data;
            
            // Create a new workbook
            const wb = XLSX.utils.book_new();
            
            // No summary worksheet - removed as requested
            
            // Process each template type
            Object.entries(formsByTemplate).forEach(([templateType, forms]) => {
                // Skip if no forms for this template
                if (forms.length === 0) return;
                
                // Get a sample form to determine structure
                const sampleForm = forms[0];
                const templateStructure = sampleForm.extractedData;
                
                // Create a summary worksheet for this template type with form details
                const templateSummaryData = [
                    [`${templateType} Forms Summary`],
                    [],
                    ['Form ID', 'File Name', 'Created Date']
                ];
                
                // Add each form to the summary
                forms.forEach(form => {
                    templateSummaryData.push([form.formId, form.fileName, form.createdAt]);
                });
                
                // Add template summary worksheet
                const templateSummaryWs = XLSX.utils.aoa_to_sheet(templateSummaryData);
                XLSX.utils.book_append_sheet(wb, templateSummaryWs, `${templateType} Summary`);
                
                // Create a detailed worksheet with all forms data in vertical format
                const detailedData = [
                    [`${templateType} - All Forms Data`],
                    []
                ];
                
                // Add each form with its data in a section-by-section format
                forms.forEach(form => {
                    // Add form header
                    detailedData.push([`Form ID: ${form.formId}`, `File: ${form.fileName}`, `Date: ${form.createdAt}`]);
                    detailedData.push([]);
                    
                    // Add all sections and their data
                    Object.entries(form.extractedData).forEach(([section, fields]) => {
                        detailedData.push([section]);
                        detailedData.push(['Field', 'Value']);
                        
                        Object.entries(fields).forEach(([field, value]) => {
                            detailedData.push([field, value || '']);
                        });
                        
                        detailedData.push([]); // Empty row after section
                    });
                    
                    detailedData.push([]); // Extra empty row between forms
                    detailedData.push([]); // Extra empty row between forms
                });
                
                // Add detailed data worksheet
                const detailedWs = XLSX.utils.aoa_to_sheet(detailedData);
                XLSX.utils.book_append_sheet(wb, detailedWs, `${templateType} Details`);
                
                // Process each section separately to get all fields
                Object.entries(templateStructure).forEach(([sectionName, fields]) => {
                    // Create headers for the section table (field names as columns)
                    const headers = ['Form ID', 'File Name', 'Created At'];
                    const fieldNames = Object.keys(fields);
                    headers.push(...fieldNames);
                    
                    // Create data rows (each form as a row)
                    const rows = [headers]; // First row is headers
                    
                    // Add a row for each form with this template
                    forms.forEach(form => {
                        const row = [
                            form.formId,
                            form.fileName,
                            form.createdAt
                        ];
                        
                        // Add values for each field
                        fieldNames.forEach(fieldName => {
                            let value = '';
                            if (form.extractedData[sectionName] && 
                                fieldName in form.extractedData[sectionName]) {
                                value = form.extractedData[sectionName][fieldName] || '';
                            }
                            row.push(value);
                        });
                        
                        rows.push(row);
                    });
                    
                    // Create and add section worksheet
                    const sectionWs = XLSX.utils.aoa_to_sheet(rows);
                    
                    // Format the worksheet - adjust column widths
                    const columnWidths = [];
                    for (let i = 0; i < headers.length; i++) {
                        // Default width is max of 15 characters or header length
                        columnWidths[i] = { wch: Math.max(15, headers[i].length * 1.2) };
                    }
                    sectionWs['!cols'] = columnWidths;
                    
                    // Create a safe sheet name (template + section)
                    const safeTemplateName = templateType.replace(/[\\/*[\]?]/g, '');
                    const safeSectionName = sectionName.replace(/[\\/*[\]?]/g, '');
                    const sheetName = `${safeTemplateName}-${safeSectionName}`.substring(0, 31);
                    XLSX.utils.book_append_sheet(wb, sectionWs, sheetName);
                });
                
                // Also create a consolidated view with all sections for this template type
                const allFields = {};
                
                // First pass: determine all fields by section
                Object.entries(templateStructure).forEach(([section, fields]) => {
                    Object.keys(fields).forEach(field => {
                        if (!allFields[section]) {
                            allFields[section] = [];
                        }
                        if (!allFields[section].includes(field)) {
                            allFields[section].push(field);
                        }
                    });
                });
                
                // Create headers for the consolidated table
                const headers = ['Form ID', 'File Name', 'Created At'];
                
                // Add all fields as headers, organized by section
                Object.entries(allFields).forEach(([section, fieldList]) => {
                    fieldList.forEach(field => {
                        headers.push(`${section} - ${field}`);
                    });
                });
                
                // Create data rows
                const rows = [headers];
                
                // Add data for each form
                forms.forEach(form => {
                    const row = [
                        form.formId,
                        form.fileName,
                        form.createdAt
                    ];
                    
                    // Add values for each field, organized by section
                    Object.entries(allFields).forEach(([section, fieldList]) => {
                        fieldList.forEach(field => {
                            let value = '';
                            if (form.extractedData[section] && 
                                field in form.extractedData[section]) {
                                value = form.extractedData[section][field] || '';
                            }
                            row.push(value);
                        });
                    });
                    
                    rows.push(row);
                });
                
                // Create the consolidated worksheet
                const templateWs = XLSX.utils.aoa_to_sheet(rows);
                
                // Format the worksheet - adjust column widths
                const mainColumnWidths = [];
                for (let i = 0; i < headers.length; i++) {
                    mainColumnWidths[i] = { wch: Math.max(15, headers[i].length * 1.2) };
                }
                templateWs['!cols'] = mainColumnWidths;
                
                // Add the consolidated worksheet
                const safeTemplateName = templateType.replace(/[\\/*[\]?]/g, '').substring(0, 28);
                XLSX.utils.book_append_sheet(wb, templateWs, safeTemplateName);
            });
            
            // Save workbook
            XLSX.writeFile(wb, `All_Forms_Export_${new Date().toISOString().split('T')[0]}.xlsx`);
            
            // Hide loading spinner
            hideSpinner();
        })
        .catch(error => {
            console.error('Error exporting all forms to Excel:', error);
            alert('Error exporting forms to Excel. Please try again.');
            hideSpinner();
        });
}
