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
        records = self.env['custody.clearance'].search([
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
        ])
        operating_costs = self.env['payment.request'].search([ 
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
            # ('state', '==', 'paid'),
            # ('is_need_clearance', '==', False),
        ])
        truck_odometers = self.env['truck.odometer'].search([
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
            # ('state', '==', 'paid'),
            # ('is_need_clearance', '==', False),
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
        sheet.write_merge(0, 0, 0, 19,  '({self.start_date})/({self.end_date}) كشف متابعة حركو وتشغيل الدفارات للفترة ', main_heading)
        sheet.write(1, 0, "رقم الشاحنة", heading)
        sheet.write(1, 1, "اسم السائق", heading)
        sheet.write(1, 2, "تاريخ التعبئة", heading)
        sheet.write(1, 3, "كمية الوقود(لتر)", heading)
        sheet.write(1, 4, "سعر الوقود(لتر)", heading)
        sheet.write(1, 5, "المسافة المقطوعة(كم)", heading)
        sheet.write(1, 6, "معدل استهلاك الوقود(لتر/كم)", heading)
        sheet.write(1, 7, "مجموع التكاليف(لتر*سعر الوقود)", heading)
        sheet.write(1, 8, "عداد المسافات", heading)
        sheet.write(1, 9, "غيار زيت الدوري", heading)
        sheet.write(1, 10, "الصيانة الدورية", heading)
        sheet.write(1, 11, "مغسلة", heading)
        sheet.write(1, 12, "بنشر", heading)
        sheet.write(1, 13, "مخالفات مرورية", heading)
        sheet.write(1, 14, "تأمين", heading)
        sheet.write(1, 15, "قيمة التأمين", heading)
        sheet.write(1, 16, "تفتيش شهري", heading)
        sheet.write(1, 17, "صيانات", heading)
        sheet.write(1, 18, "الاجمالي", heading)
        sheet.write(1, 19, "ملاحظات", heading)
        
        row = 2   
        total_oil_change = total_maintenance = total_car_wash = total_car_tire_repair = total_violations = total_insurance = 0
        for rec in operating_costs:
            if rec.state == "paid":    
                sheet.row(row).height = 400
                sheet.write(row, 0, rec.vehicle_id.license_plate, content_format) 
                sheet.write(row, 1, rec.vehicle_id.driver_id.name, content_format) 
                sheet.write(row, 2, rec.date.strftime('%d/%m/%Y'), content_format)
                # sheet.write(row, 1, rec.request_id.name, content_format)
                # sheet.write(row, 2, rec.employee_id.name, content_format)
                # sheet.write(row, 3, rec.custody_amount, content_format)
                # sheet.write(row, 4, "-", content_format)
                # sheet.write(row, 5, rec.request_id.base_amount, content_format)
                # sheet.write(row, 6, "استلام", content_format1)
                # sheet.write(row, 7, "" , content_format)
                # sheet.write(row, 8, ref, content_format) 
                if rec.custody_type == 'oil_change':
                    sheet.write(row, 9, rec.total_amount, content_format) 
                    total_oil_change += rec.total_amount
                if rec.custody_type == 'maintenance':
                    sheet.write(row, 10, rec.total_amount, content_format) 
                    total_maintenance += rec.total_amount
                if rec.custody_type == 'car_wash':
                    sheet.write(row, 11, rec.total_amount, content_format) 
                    total_car_wash += rec.total_amount
                if rec.custody_type == 'car_tire_repair':
                    sheet.write(row, 12, rec.total_amount, content_format) 
                    total_car_tire_repair += rec.total_amount
                if rec.custody_type == 'violations':
                    sheet.write(row, 13, rec.total_amount, content_format)  
                    total_violations += rec.total_amount
                if rec.custody_type == 'insurance':
                    sheet.write(row, 14, rec.total_amount, content_format)  
                    total_insurance += rec.total_amount
                row += 1 
 
        sheet.row(row).height = 400
        sheet.write(row, 0, "المجموع", currency_format)
        sheet.write(row, 1, "-", currency_format)
        sheet.write(row, 2, "-", currency_format)
        # sheet.write(row, 3,  , currency_format)
        # sheet.write(row, 4,  , currency_format)
        sheet.write(row, 5, "-", currency_format)
        sheet.write(row, 6, row-2, currency_format)
        sheet.write(row, 7, row-2, currency_format)
        sheet.write(row, 8, "-", currency_format) 
        sheet.write(row, 9, total_oil_change , currency_format)
        sheet.write(row, 10, total_maintenance , currency_format)
        sheet.write(row, 11, total_car_wash , currency_format)
        sheet.write(row, 12, total_car_tire_repair , currency_format) 
        sheet.write(row, 13, total_violations , currency_format) 
        sheet.write(row, 14, total_insurance , currency_format) 
    
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