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
            
            // Create consolidated data worksheet
            const allData = [
                [`${templateType} Form - Complete Data`],
                [],
                ['Section', 'Field', 'Value']
            ];
            
            // Add all fields with their sections
            Object.entries(extractedData).forEach(([section, fields]) => {
                Object.entries(fields).forEach(([field, value]) => {
                    allData.push([section, field, value || '']);
                });
            });
            
            // Add consolidated worksheet
            const allDataWs = XLSX.utils.aoa_to_sheet(allData);
            XLSX.utils.book_append_sheet(wb, allDataWs, 'All Data');
            
            // Create section-specific worksheets
            Object.entries(extractedData).forEach(([section, fields]) => {
                const sectionData = [
                    [section],
                    [],
                    ['Field', 'Value']
                ];
                
                // Add all fields for this section
                Object.entries(fields).forEach(([field, value]) => {
                    sectionData.push([field, value || '']);
                });
                
                // Create and add section worksheet
                const sectionWs = XLSX.utils.aoa_to_sheet(sectionData);
                const safeSheetName = section.replace(/[\\/*[\]?]/g, '').substring(0, 31);
                XLSX.utils.book_append_sheet(wb, sectionWs, safeSheetName);
            });
            
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
