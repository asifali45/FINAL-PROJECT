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
            
            // Add table of contents
            doc.setFont(undefined, 'bold');
            doc.setFontSize(14);
            doc.text('Form Sections:', 20, 50);
            
            let tocY = 60;
            const sections = Object.keys(extractedData);
            sections.forEach((section, index) => {
                doc.setFont(undefined, 'normal');
                doc.setFontSize(12);
                doc.text(`${index + 1}. ${section}`, 25, tocY);
                tocY += 8;
            });
            
            // Add line separator after TOC
            tocY += 5;
            doc.line(20, tocY, 190, tocY);
            tocY += 10;
            
            // Check if we need to add a new page for the form data
            if (tocY > 240) {
                doc.addPage();
                tocY = 20;
            }
            
            // Set starting y position for form sections
            let yPos = tocY;
            
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
    
    // Fetch the form data
    fetch(`/export-form/${formId}/json`)
        .then(response => response.json())
        .then(data => {
            const { templateType, fileName, extractedData } = data;
            
            // Create a new workbook
            const wb = XLSX.utils.book_new();
            
            // Create a summary worksheet
            const summaryData = [
                [`${templateType} Form`],
                ['Original File:', fileName],
                ['Export Date:', new Date().toLocaleString()],
                [],
                ['Form Sections:']
            ];
            
            // Add sections to summary
            Object.keys(extractedData).forEach((section, index) => {
                summaryData.push([`${index + 1}. ${section}`]);
            });
            
            // Add summary worksheet
            const summaryWs = XLSX.utils.aoa_to_sheet(summaryData);
            XLSX.utils.book_append_sheet(wb, summaryWs, 'Summary');
            
            // Create section-specific worksheets - one per section
            Object.entries(extractedData).forEach(([section, fields]) => {
                // Create section data with proper column headers
                const headers = Object.keys(fields);
                
                // Create the data rows for this section
                const rows = [];
                rows.push(headers); // First row is field names
                rows.push(Object.values(fields).map(val => val || '')); // Second row is values
                
                // Create and add worksheet
                const sectionWs = XLSX.utils.aoa_to_sheet(rows);
                
                // Format the worksheet - adjust column widths
                const columnWidths = [];
                for (let i = 0; i < headers.length; i++) {
                    // Default width is max of 15 characters or header length
                    columnWidths[i] = { wch: Math.max(15, headers[i].length * 1.2) };
                }
                sectionWs['!cols'] = columnWidths;
                
                // Create a safe sheet name
                const safeSheetName = section.replace(/[\\/*[\]?]/g, '').substring(0, 31);
                XLSX.utils.book_append_sheet(wb, sectionWs, safeSheetName);
            });
            
            // Create consolidated data worksheet in the format requested
            // This will have field names as columns
            const allHeaders = [];
            const allValues = [];
            
            // Extract all field names by section
            Object.entries(extractedData).forEach(([section, fields]) => {
                Object.entries(fields).forEach(([field, value]) => {
                    allHeaders.push(`${section} - ${field}`);
                    allValues.push(value || '');
                });
            });
            
            // Create the consolidated data
            const allData = [
                allHeaders, // Field names as columns
                allValues   // Values as a row
            ];
            
            // Add consolidated worksheet
            const allDataWs = XLSX.utils.aoa_to_sheet(allData);
            
            // Format the consolidated worksheet
            const allColumnWidths = [];
            for (let i = 0; i < allHeaders.length; i++) {
                allColumnWidths[i] = { wch: Math.max(15, allHeaders[i].length * 1.2) };
            }
            allDataWs['!cols'] = allColumnWidths;
            
            XLSX.utils.book_append_sheet(wb, allDataWs, 'All Fields');
            
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
    
    // Fetch all forms data
    fetch('/export-all-forms/json')
        .then(response => response.json())
        .then(data => {
            const { username, exportDate, formsByTemplate } = data;
            
            // Create a new workbook
            const wb = XLSX.utils.book_new();
            
            // Create a summary worksheet
            const summaryData = [
                ['Form Digitizer - All Forms Export'],
                ['User:', username],
                ['Export Date:', exportDate],
                [],
                ['Templates Included:']
            ];
            
            // Add template types to summary
            Object.keys(formsByTemplate).forEach((template, index) => {
                const formCount = formsByTemplate[template].length;
                summaryData.push([`${index + 1}. ${template} (${formCount} forms)`]);
            });
            
            // Add summary worksheet
            const summaryWs = XLSX.utils.aoa_to_sheet(summaryData);
            XLSX.utils.book_append_sheet(wb, summaryWs, 'Summary');
            
            // Process each template type
            Object.entries(formsByTemplate).forEach(([templateType, forms]) => {
                // Skip if no forms for this template
                if (forms.length === 0) return;
                
                // Get a sample form to determine structure
                const sampleForm = forms[0];
                const templateStructure = sampleForm.extractedData;
                
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
