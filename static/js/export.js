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
            
            // Loop through each section in the extracted data
            for (const [section, fields] of Object.entries(extractedData)) {
                // Add section header
                doc.setFont(undefined, 'bold');
                doc.setFontSize(14);
                doc.text(section, 20, yPos);
                yPos += 10;
                
                // Add fields
                doc.setFont(undefined, 'normal');
                doc.setFontSize(11);
                
                for (const [field, value] of Object.entries(fields)) {
                    // Check if we need to add a new page
                    if (yPos > 270) {
                        doc.addPage();
                        yPos = 20;
                    }
                    
                    // Add field and value
                    doc.text(`${field}: ${value}`, 25, yPos);
                    yPos += 7;
                }
                
                // Add space between sections
                yPos += 5;
                
                // Check if we need to add a new page for the next section
                if (yPos > 260) {
                    doc.addPage();
                    yPos = 20;
                }
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
            
            // Prepare data for worksheet
            const excelData = [];
            
            // Add header row
            excelData.push(['Section', 'Field', 'Value']);
            
            // Add data rows
            for (const [section, fields] of Object.entries(extractedData)) {
                for (const [field, value] of Object.entries(fields)) {
                    excelData.push([section, field, value]);
                }
            }
            
            // Create worksheet
            const ws = XLSX.utils.aoa_to_sheet(excelData);
            
            // Add worksheet to workbook
            XLSX.utils.book_append_sheet(wb, ws, templateType);
            
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
