from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.chart import BarChart, Reference, PieChart, LineChart
from collections import Counter
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
    
class SalesReportExcel(ExcelReportGenerator):
    '''Sales report Excel generator'''
    
    def __init__(self, date_from, date_to, sales_data, summary):
        title = f"Sales Report: {date_from.strftime('%d %B, %Y')} to {date_to.strftime('%d %B, %Y')}"
        super().__init__(title)
        self.date_from = date_from
        self.date_to = date_to
        self.sales_data = sales_data
        self.summary = summary
        
    def build(self):
        '''Build the sales report'''
        sheet = self.create_sheet('Sales Report')
        
        #Title
        self.add_title(sheet, self.title)
        self.add_date(sheet, row=2)
        
        #Summary Section
        summary_data = {
            'Total Sales': self.summary['total_sales'],
            'Total Revenue': f"UGX {self.summary['total_revenue'],}",
            'Average Sale': f"UGX {self.summary['average_sale']:,.0f}",
            'Total Customers': self.summary['total_customers'],
        }
        data_start_row = self.add_summary_section(sheet, summary_data, start_row=4)
        
        #Sales data table
        headers = ['Date', 'Customer', "Items", 'Amount(UGX)', 'Status']
        for col_num, header in enumerate(headers, 1):
            sheet.cell(row=data_start_row, column=col_num, value=header)
        self.style_header_row(sheet, data_start_row, headers)
        
        # Add data
        row = data_start_row + 1
        for sale in self.sales_data:
            sheet[f'A{row}'] = sale['date'].strftime('%m/%d/%Y')
            sheet[f'B{row}'] = sale['customer']
            sheet[f'C{row}'] = sale['items']
            sheet[f'D{row}'] = sale['amount']
            sheet[f'E{row}'] = sale['status']
            
            # Apply borders
            for col in range(1,6):
                sheet.cell(row=row, column=col).border= self.border
                
            row += 1
            
            # Auto-adjust columns
            self.auto_adjust_columns(sheet)
            
            #Add chart if we have data
            if len(self.sales_data) > 0:
                self.add_sales_chart(sheet, data_start_row, row - 1)
                self.add_revenue_line_chart(sheet, data_start_row, row - 1)
                self.add_status_pie_chart()
            return self
        
        def add_sales_chart(self, sheet, start_row, end_row):
            '''Add a sales chart'''
            #Create a new sheet for chart
            chart_sheet =self.create_sheet('Sales Chart')
            
            #Create bar chart
            chart = BarChart()
            chart.title = 'Sales by Date'
            chart.x_axis.title = 'Date'
            chart.y_axis.title = 'Amount (UGx)'
            
            # Set data
            data = Reference(sheet, min_col=4, min_row=start_row, max_row=end_row)
            categories = Reference(sheet, min_col=1, min_row=start_row+1, max_row=end_row)
            
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(categories)
            
            chart_sheet.add_chart(chart, 'A1')
        
        def add_revenue_line_chart(self, sheet, start_row, end_row):
            chart_sheet = self.create_sheet("Revenue Trend")
            
            #Create a line chart
            chart = LineChart()
            chart.title = 'Cumulative Revenue Over Time'
            chart.x_axis.title = "Date"
            chart.y_axis.title = "Revenue (UGX)"
            chart.style = 13

            data = Reference(sheet, min_col=4, min_row=start_row, max_row=end_row)
            categories = Reference(sheet, min_col=1, min_row=start_row + 1, max_row=end_row)

            chart.add_data(data, titles_from_data=True)
            chart.set_categories(categories)

            chart_sheet.add_chart(chart, "A1")


        def add_status_pie_chart(self):
            chart_sheet = self.create_sheet("Status Breakdown")

            # Count statuses
            status_counts = Counter(sale['status'] for sale in self.sales_data)

            # Write data to sheet
            chart_sheet['A1'] = "Status"
            chart_sheet['B1'] = "Count"
            row = 2
            for status, count in status_counts.items():
                chart_sheet[f'A{row}'] = status
                chart_sheet[f'B{row}'] = count
                row += 1

            # Create pie chart
            chart = PieChart()
            chart.title = "Sales Status Breakdown"
            data = Reference(chart_sheet, min_col=2, min_row=1, max_row=row - 1)
            labels = Reference(chart_sheet, min_col=1, min_row=2, max_row=row - 1)

            chart.add_data(data, titles_from_data=True)
            chart.set_categories(labels)

            chart_sheet.add_chart(chart, "D2")

class InventoryReportExcel(ExcelReportGenerator):
    """Inventory report Excel generator"""
    
    def __init__(self, inventory_data, summary):
        super().__init__("Inventory Status Report")
        self.inventory_data = inventory_data
        self.summary = summary
    
    def build(self):
        """Build the inventory report"""
        # Create inventory sheet
        sheet = self.create_sheet("Inventory Report")

        # Title and date
        self.add_title(sheet, self.title)
        self.add_date(sheet, row=2)

        # Summary section
        summary_data = {
            'Total Products': self.summary['total_products'],
            'Low Stock Items': self.summary['low_stock'],
            'Out of Stock': self.summary['out_of_stock'],
            'Total Inventory Value': f"UGX {self.summary['total_value']:,}",
        }
        data_start_row = self.add_summary_section(sheet, summary_data, start_row=4)

        # Table headers
        headers = ['Product', 'Variant', 'Current Stock', 'Reorder Level', 'Status']
        for col_num, header in enumerate(headers, 1):
            sheet.cell(row=data_start_row, column=col_num, value=header)
        self.style_header_row(sheet, data_start_row, headers)

        # Table data
        row = data_start_row + 1
        for item in self.inventory_data['low_stock']:
            status = "OUT OF STOCK" if item['stock'] == 0 else "LOW STOCK"

            sheet[f'A{row}'] = item['product']
            sheet[f'B{row}'] = item['variant']
            sheet[f'C{row}'] = item['stock']
            sheet[f'D{row}'] = item['reorder_level']
            sheet[f'E{row}'] = status

            # Color-code status
            status_cell = sheet[f'E{row}']
            if status == "OUT OF STOCK":
                status_cell.fill = PatternFill(start_color='FF0000', end_color='FF0000', fill_type='solid')
                status_cell.font = Font(color='FFFFFF', bold=True)
            else:
                status_cell.fill = PatternFill(start_color='FFC107', end_color='FFC107', fill_type='solid')

            # Highlight critical stock
            if item['stock'] < item['reorder_level']:
                sheet[f'C{row}'].fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')

            # Apply borders
            for col in range(1, 6):
                sheet.cell(row=row, column=col).border = self.border

            row += 1

        # Auto-adjust columns
        self.auto_adjust_columns(sheet)

        # Add pie chart for stock status breakdown
        if self.summary['low_stock'] or self.summary['out_of_stock']:
            chart_sheet = self.create_sheet("Stock Status Chart")
            chart_sheet['A1'] = "Status"
            chart_sheet['B1'] = "Count"
            chart_sheet['A2'] = "LOW STOCK"
            chart_sheet['B2'] = self.summary['low_stock']
            chart_sheet['A3'] = "OUT OF STOCK"
            chart_sheet['B3'] = self.summary['out_of_stock']

            chart = PieChart()
            chart.title = "Stock Status Breakdown"
            data = Reference(chart_sheet, min_col=2, min_row=1, max_row=3)
            labels = Reference(chart_sheet, min_col=1, min_row=2, max_row=3)
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(labels)
            chart_sheet.add_chart(chart, "D2")

        return self
