from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.chart import BarChart, Reference, PieChart
from datetime import datetime

class ExcelReportGenerator:
    '''Base class for generating Excel reports'''
    
    def __init__(self, title):
        self.title = title
        self.workbook = Workbook()
        self.workbook.remove(self.workbook.active) #Removethe default sheet
        
        # Define styles
        self.header_font = Font(name='Arial', size=14, bold=True, color='FFFFFF')
        self.header_fill = PatternFill(start_color='2C5F2D', end_color='2C5F2D', fill_type='solid')
        self.title_font = Font(name='Arial', size=18, bold=True, color='2C5F2D')
        self.border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
    
    def create_sheet(self, name):
        '''Create a new worksheet'''
        sheet = self.workbook.create_sheet(title=name)
        return sheet
    
    def add_title(self, sheet, title, row=1):
        '''Add a title to the sheet'''
        sheet.merge_cells(f'A{row}:E{row}')
        cell = sheet[f'A{row}']
        cell.value = title
        cell.font = self.title_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        sheet.row_dimensions[row].height = 30
        
    def add_date(self, sheet, row=2):
        '''Add generation date'''
        sheet.merge_cells(f'A{row}:E{row}')
        cell = sheet[f'A{row}']
        cell.value = f"Generated:{datetime.now().strftime('%d %B, %Y at %I:%M %p')}"
        cell.alignment = Alignment(horizontal='center')
        cell.font = Font(size=10, italic=True)
        
    def style_header_row(self, sheet, row, columns):
        '''Style the header rows'''
        for col_num, _ in enumerate(columns, 1):
            cell = sheet.cell(row=row, column=col_num)
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = self.border
        sheet.row_dimensions[row].height = 20
        
    def add_summary_section(self, sheet, summary_data, start_row):
        '''Add summary statistics'''
        sheet.merge_cells(f'A{start_row}:B{start_row}')
        cell = sheet[f'A{start_row}']
        cell.value = 'Summary'
        cell.font = Font(size=12, bold = True)
        
        row = start_row + 1
        for label, value in summary_data.items():
            sheet[f'A{row}'] = label
            sheet[f'B{row}'] = value
            sheet[f'A{row}'].font = Font(bold=True)
            sheet[f'A{row}'].border = self.border
            sheet[f'B{row}'].border = self.border
            row += 1
        return row + 1
    
    def auto_adjust_columns(self, sheet):
        '''Auto-adjust column widths'''
        for column in sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjused_width = min(max_length + 2, 50)
            sheet.column_dimensions[column_letter].width = adjused_width
            
    def save(self, buffer):
        '''Save the workbook to buffer'''
        self.workbook.save(buffer)
        return buffer