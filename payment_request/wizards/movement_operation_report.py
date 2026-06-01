import base64
from io import BytesIO
from locale import currency
import xlwt
from odoo import fields, api, models, _
from odoo.exceptions import ValidationError

class MovementOperationReport(models.TransientModel): 
    _name = 'movement.operation.report'
    _description = __doc__

    start_date = fields.Date()
    end_date = fields.Date()

    @api.constrains('start_date', 'end_date')
    def _check_movement_operation_report_date_check(self):
        """Check if end date is after start date"""
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_("End date cannot be earlier than start date."))

    def action_generate_movement_operation_excel(self):
        """Generate and return Excel file for movement operation"""
       
        operating_costs = self.env['payment.request'].search([ 
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
            ('state', '=', 'paid'),
            ('is_need_clearance', '=', False),
        ])
        

        workbook = xlwt.Workbook(encoding='utf-8')
        sheet = workbook.add_sheet('movement operation', cell_overwrite_ok=True)
        sheet.cols_right_to_left = True
        # Styles 
        main_heading = xlwt.easyxf('align: wrap on, horiz center, vert center; font: bold True, height 320;pattern:pattern solid,fore_colour light_blue;borders: left thin, right thin, top thin, bottom thin;',num_format_str="#,##0.00")
        heading = xlwt.easyxf('align: wrap on, horiz center, vert center; font: height 270;pattern:pattern solid,fore_colour light_green;',num_format_str="#,##0.00")
        content_format = xlwt.easyxf('align:horiz center,  vert center; font: height 220;',num_format_str="#,##0.00")
        content_format1 = xlwt.easyxf('align:horiz center,  vert center; font: height 220; pattern:pattern solid,fore_colour light_green;',num_format_str="#,##0.00")
        content_format2 = xlwt.easyxf('align:horiz center,  vert center; font: height 220;pattern:pattern solid,fore_colour rose;',num_format_str="#,##0.00")
        content_format3 = xlwt.easyxf('align:horiz center,  vert center; font: height 270;pattern:pattern solid,fore_colour red;',num_format_str="#,##0.00")
        currency_format = xlwt.easyxf('align:horiz center, vert center; font: bold True, height 320;pattern:pattern solid,fore_colour light_blue;',num_format_str="#,##0.00")

        # Define styles
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'dd/mm/yyyy'

        # Set row widths
        sheet.row(0).height = 700
        sheet.row(1).height = 700

        # Set column widths
        sheet.col(0).width = 3000
        sheet.col(1).width = 4000
        sheet.col(2).width = 4000
        sheet.col(3).width = 4000
        sheet.col(4).width = 4000
        sheet.col(5).width = 4000
        sheet.col(6).width = 4000
        sheet.col(7).width = 4000
        sheet.col(8).width = sheet.col(9).width = sheet.col(10).width = sheet.col(11).width = sheet.col(12).width = sheet.col(13).width = sheet.col(14).width = sheet.col(15).width =sheet.col(16).width =sheet.col(17).width =sheet.col(18).width=sheet.col(19).width = 5000

        # Write header
        sheet.write_merge(0, 0, 0, 14,  f'({self.end_date})/({self.start_date}) كشف متابعة و تشغيل الدفارات للفترة ', main_heading)
        sheet.write(1, 0, "رقم الشاحنة", heading)
        sheet.write(1, 1, "اسم السائق", heading)
        sheet.write(1, 2, "تاريخ التعبئة", heading)
        sheet.write(1, 3, "كمية الوقود(لتر)", heading)
        sheet.write(1, 4, "سعر الوقود(لتر)", heading)
        sheet.write(1, 5, "عداد المسافات", heading)
        # sheet.write(1, 6, "معدل استهلاك الوقود(لتر/كم)", heading)
        sheet.write(1, 6, "مجموع التكاليف(لتر*سعر الوقود)", heading)
        sheet.write(1, 7, "الصيانة", heading)
        sheet.write(1, 8, "مغسلة", heading)
        sheet.write(1, 9, "بنشر", heading)
        sheet.write(1, 10, "مخالفات حكومية", heading)
        sheet.write(1, 11, "تأمين", heading)
        sheet.write(1, 12, "تفتيش شهري", heading)
        sheet.write(1, 13, "أخرى", heading) 
        sheet.write(1, 14, "ملاحظات", heading)
        
        row = 2   
        total_oil_change = total_maintenance = total_car_wash = total_car_tire_repair = total_violations = total_insurance = total_monthly_inspection = total_other = 0
        for rec in operating_costs:  
            fuel_quantity = 0
            fuel_price = 0
            fuel_amount = 0
            date = rec.date
            vehicle = rec.vehicle_id 
            vehicle_odometers = 0
            records = self.env['custody.clearance'].search([ 
                ('date', '=', date),
                ('vehicle_id', '=', vehicle),
                ('state', '=', 'done'),
            ]) 
            if records:
                for rec in  records:
                    fuel_quantity += rec.custody_line_ids.quantity
                    fuel_price += rec.custody_line_ids.price_unit
                    fuel_amount += rec.custody_line_ids.amount
            truck_odometers = self.env['fleet.vehicle.odometer'].search([ 
                ('date', '=', date), 
                ('vehicle_id', '=', vehicle),
            ])
            if truck_odometers :
                for rec in  truck_odometers:
                    vehicle_odometers = rec.value 
            sheet.row(row).height = 400
            sheet.write(row, 0, rec.vehicle_id.license_plate, content_format) 
            sheet.write(row, 1, rec.vehicle_id.driver_id.name, content_format) 
            sheet.write(row, 2, rec.date.strftime('%d/%m/%Y'), content_format) 
            sheet.write(row, 3, fuel_quantity, content_format) 
            sheet.write(row, 4, fuel_price, content_format) 
            sheet.write(row, 5, vehicle_odometers, content_format) 
            sheet.write(row, 6, fuel_amount, content_format) 
            if rec.custody_type == 'maintenance':
                sheet.write(row, 7, rec.total_amount, content_format) 
                total_maintenance += rec.total_amount
            if rec.custody_type == 'car_wash':
                sheet.write(row, 8, rec.total_amount, content_format) 
                total_car_wash += rec.total_amount
            if rec.custody_type == 'car_tire_repair':
                sheet.write(row, 9, rec.total_amount, content_format) 
                total_car_tire_repair += rec.total_amount
            if rec.custody_type == 'violations':
                sheet.write(row, 10, rec.total_amount, content_format) 
                total_violations += rec.total_amount 
            if rec.custody_type == 'insurance':
                sheet.write(row, 11, rec.total_amount, content_format)  
                total_insurance += rec.total_amount
            if rec.custody_type == 'monthly_inspection':
                sheet.write(row, 12, rec.total_amount, content_format)  
                total_monthly_inspection += rec.total_amount
            if rec.custody_type == 'other':
                sheet.write(row, 13, rec.total_amount, content_format)  
                total_other += rec.total_amount
            sheet.write(row, 14, rec.niration, content_format)  
            row += 1  
                
        sheet.row(row).height = 400
        sheet.write(row, 0, "المجموع", currency_format)
        sheet.write(row, 1, "-", currency_format)
        sheet.write(row, 2, "-", currency_format)
        sheet.write(row, 3, "" , currency_format)
        sheet.write(row, 4, "", currency_format)
        sheet.write(row, 5, "-", currency_format)
        sheet.write(row, 6, row-2, currency_format) 
        sheet.write(row, 7, total_maintenance , currency_format)
        sheet.write(row, 8, total_car_wash , currency_format)
        sheet.write(row, 9, total_car_tire_repair , currency_format)
        sheet.write(row, 10, total_violations , currency_format) 
        sheet.write(row, 11, total_insurance , currency_format) 
        sheet.write(row, 12, total_monthly_inspection , currency_format) 
        sheet.write(row, 13, total_other, currency_format) 
        sheet.write(row, 14, "", currency_format) 
    
        stream = BytesIO()
        workbook.save(stream)
        out = base64.encodebytes(stream.getvalue())

        # Create attachment
        attachment = self.env['ir.attachment'].sudo().create({
            'name': f'Movement Operation({self.start_date})/({self.end_date}) Report.xls',
            'type': 'binary',
            'public': False,
            'datas': out,
        })
        # Return download action
        if attachment:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'new',
            }
        return True
