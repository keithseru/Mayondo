from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime
import io

class PDFReportGenerator:
    '''BAse class fro generating PDF reports'''
    
    def __init__(self, title, orientation='potrait'):
        self.title = title
        self.pagesize = A4 if orientation == "potrait" else (A4[1], A4[0])
        self.styles = getSampleStyleSheet()
        self.elements = []
        
        #Custom Styles
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2c5f2d'),
            spaceAfter=30,
            alignment=TA_CENTER,
        )
        
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c5f2d'),
            spaceAfter=12,
        )
        
    def add_header(self, company_name='MayondoWood Ltd'):
        '''Add report header'''
        # Company name
        company = Paragraph(f"<b>{company_name}</b>", self.title_style)
        self.elements.append(company)
        
        #Report Title
        title = Paragraph(self.title, self.heading_style)
        self.elements.append(title)
        
        # Date generation
        date_style = ParagraphStyle(
            'DateStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            alignment=TA_RIGHT,
        )
        date_text = f'Generated: {datetime.now().strftime('%d %B, %Y at %I:%M %p')}'
        date_paragraph = Paragraph(date_text, date_style)
        self.elements.append(date_paragraph)
        
    def add_summary_boxes(self, summary_data):
        '''Add summary statistics boxes'''
        #Create table for summary
        data = []
        row = []
        
        for item in summary_data:
            row.append([
                Paragraph(f"<b>{item['label']}</b>", self.styles['Normal']),
                Paragraph(f"<font size=18 color='#2c5f2d'><b>{item['value']}</b></font>", self.styles['Normal'])
            ])
            if len(row) == 2:
                data.append(row)
                row = []
            
        if row: #Add remianing items
            while len(row) < 2:
                row.append(['',''])
            data.append(row)
            
        if data:
            table = Table(data, colWidths = [2.5*inch, 2.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('PADDING', (0, 0), (-1, -1), 12),
            ]))
            self.elements.append(table)
            self.elements.append(Spacer(1, 20))
            
    def add_table(self, headers, rows, col_widths=None):
        '''Add a data table'''
        # Prepare the data
        table_data = [headers]
        table_data.extend(rows)
        
        #Create table
        if col_widths:
            table = Table(table_data, colWidths=col_widths)
        else: 
            table = Table(table_data)
            
        #Style the Table
        table.setStyle(TableStyle([
            #Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5f2d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Body
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
            
            # Alternating rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1,20))
        
    def add_section_heading(self, text):
        '''Add a section heading'''
        heading = Paragraph(text, self.heading_style)
        self.elements.append(heading)
        self.elements.append(Spacer(1, 10))
        
    def generate(self, buffer):
        '''Generate the PDF document'''
        doc = SimpleDocTemplate(
            buffer,
            pagesize = self.pagesize,
            rightMargin = 72,
            leftMargin = 72,
            topMargin = 72,
            bottomMargin=72,
        )
        
        #Build PDF
        doc.build(self.elements)
        return buffer
    
class SalesReportPDF(PDFReportGenerator):
    '''Sales report PDF generator'''
    
    def __init__(self, date_from, date_to, sales_data, summary):
        title = f"Sales Report: {date_from.strftime('%d %B, %Y')} to {date_to.strftime('%d %B, %Y')}" 
        super().__init__(title)
        self.date_from = date_from
        self.date_to = date_to
        self.sales_data = sales_data
        self.summary = summary
        
    def build(self):
        '''Build the sales report'''
        #Header
        self.add_header()
        
        # Summary boxes
        summary_data = [
            {'label': 'Total Sales', 'value': self.summary['total_sales']},
            {'label': 'Total Revenue', 'value': f"UGX {self.summary['total_revenue']:,}"},
            {'label': 'Average Sale', 'value': f"UGX {self.summary['average_sale']:,.0f}"},
            {'label': 'Total Customers', 'value': self.summary['total_customers']},
        ]
        
        self.add_summary_boxes(summary_data)
        
        # Sales table
        self.add_section_heading("Sales Transactions")
        headers = ['Date', 'Customer', 'Items', 'Amount', 'Status']
        rows = []
        
        for sale in self.sales_data:
            rows.append([
                sale['date'].strftime('%d/%m/%Y'),
                sale['customer'],
                str(sale['items']),
                f"UGX {sale['amount']:,}",
                sale['status']
            ])
        self.add_table(headers, rows, col_widths=[1.2*inch, 2*inch, 0.8*inch, 1.5*inch, 1*inch])
        
        return self
    
class InventoryReportPDF(PDFReportGenerator):
    '''Inventory report PDF generator'''
    
    def __init__(self, inventory_data, summary):
        super().__init__('Inventory Status Report')
        self.inventory_data = inventory_data
        self.summary = summary
        
    def build(self):
        '''Build the inventory report'''
        # Header
        self.add_header()
        
        #summary boxes
        summary_data = ([
            {'label': 'Total Products', 'value': self.summary['total_products']},
            {'label': 'Low Stock Items', 'value': self.summary['low_stock']},
            {'label': 'Out of Stock', 'value': self.summary['out_of_stock']},
            {'label': 'Total Value', 'value': f"UGX {self.summary['total_value']:,}"},
        ])
        self.add_summary_boxes(summary_data)
        
        # Low stock items
        if self.inventory_data['low_stock']:
            self.add_section_heading('Low Stock Items(Urgent Attention Required)')
            headers = ['Product', 'Variant', 'Current Stock', 'Reorder Level', 'Status']
            rows = []
            
            for item in self.inventory_data['low_stock']:
                status = 'OUT OF STOCK' if item['stock'] == 0 else 'LOW STOCK'
                rows.append([
                    item['product'],
                    item['variant'],
                    str(item['stock']),
                    str(item['reorder_level']),
                    status
                ])
            self.add_table(headers, rows, col_widths=[2*inch, 1.5*inch, 1*inch, 1*inch, 1*inch])
        return self