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
            
            // Create a summary worksheet first
            const summaryData = [];
            
            // Add title and metadata
            summaryData.push([`${templateType} Form`]);
            summaryData.push(['Original File:', fileName]);
            summaryData.push(['Export Date:', new Date().toLocaleString()]);
            summaryData.push([]);  // Empty row
            summaryData.push(['Form Sections:']);
            
            // List all sections
            Object.keys(extractedData).forEach((section, index) => {
                summaryData.push([`${index + 1}. ${section}`]);
            });
            
            // Create and add the summary worksheet
            const summaryWs = XLSX.utils.aoa_to_sheet(summaryData);
            XLSX.utils.book_append_sheet(wb, summaryWs, 'Summary');
            
            // Create a nicely formatted main worksheet with all data
            const mainData = [];
            
            // Add title row
            mainData.push([`${templateType} Form Data`]);
            mainData.push([]); // Empty row
            
            // Process each section
            for (const [section, fields] of Object.entries(extractedData)) {
                // Add section header
                mainData.push([section]);
                
                // Add column headers
                const headers = ['Field', 'Value'];
                mainData.push(headers);
                
                // Add field data
                for (const [field, value] of Object.entries(fields)) {
                    mainData.push([field, value]);
                }
                
                // Add empty row between sections
                mainData.push([]);
            }
            
            // Create and add main worksheet
            const mainWs = XLSX.utils.aoa_to_sheet(mainData);
            XLSX.utils.book_append_sheet(wb, mainWs, 'All Data');
            
            // Create individual worksheets for each section
            for (const [section, fields] of Object.entries(extractedData)) {
                // Prepare data for this section's worksheet
                const sectionData = [];
                
                // Add section title
                sectionData.push([section]);
                sectionData.push([]); // Empty row
                
                // Get all field names for this section
                const fieldNames = Object.keys(fields);
                
                // Add header row
                sectionData.push(fieldNames);
                
                // Add data row
                const values = fieldNames.map(field => fields[field]);
                sectionData.push(values);
                
                // Create worksheet
                const sectionWs = XLSX.utils.aoa_to_sheet(sectionData);
                
                // Sanitize section name for sheet name (max 31 chars, no special chars)
                const sheetName = section.replace(/[\\/*[\]?]/g, '').substring(0, 31);
                
                // Add worksheet to workbook
                XLSX.utils.book_append_sheet(wb, sectionWs, sheetName);
            }
            
            // Save the Excel file
            XLSX.writeFile(wb, `${templateType.replace(' ', '_')}_Form_${formId}.xlsx`);
            
            // Hide loading spinner
            hideSpinner();
        })
        .catch(error => {
            console.error('Error exporting to Excel:', error);
            alert('Error exporting to Excel. Please try again.');
            hideSpinner();
        });
}
