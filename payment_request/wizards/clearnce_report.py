import base64
from io import BytesIO
from locale import currency
import xlwt
from odoo import fields, api, models, _
from odoo.exceptions import ValidationError

class ClearnceReport(models.TransientModel): 
    _name = 'clearnce.report'
    _description = __doc__

    start_date = fields.Date()
    end_date = fields.Date()

    @api.constrains('start_date', 'end_date')
    def _check_clearnce_report_date_check(self):
        """Check if end date is after start date"""
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_("End date cannot be earlier than start date."))

    def action_generate_clearnce_excel(self):
        """Generate and return Excel file for clearnce"""
         
        workbook = xlwt.Workbook(encoding='utf-8')
        sheet = workbook.add_sheet('Clearance', cell_overwrite_ok=True)
        sheet.cols_right_to_left = True
        # Styles
        main_heading = xlwt.easyxf('align: wrap on, horiz center, vert center; font: bold True, height 320;pattern:pattern solid,fore_colour light_blue;',num_format_str="#,##0.00")
        heading = xlwt.easyxf('align: wrap on, horiz center, vert center; font: height 270;pattern:pattern solid,fore_colour light_green;',num_format_str="#,##0.00")
        content_format = xlwt.easyxf('align:horiz center,  vert center; font: height 220;',num_format_str="#,##0.00")
        content_format1 = xlwt.easyxf('align:horiz center,  vert center; font: height 220; pattern:pattern solid,fore_colour light_green;',num_format_str="#,##0.00")
        content_format2 = xlwt.easyxf('align:horiz center,  vert center; font: height 220;pattern:pattern solid,fore_colour rose;',num_format_str="#,##0.00")
        content_format3 = xlwt.easyxf('align:horiz center,  vert center; font: height 270;pattern:pattern solid,fore_colour red;',num_format_str="#,##0.00")
        currency_format = xlwt.easyxf('align:horiz center, vert center; font: height 220;',num_format_str="#,##0.00")


        # Define styles
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'dd/mm/yyyy'

        # Set row widths
        sheet.row(0).height = 500
        sheet.row(1).height = 700

        # Set column widths
        sheet.col(0).width = 3000
        sheet.col(1).width = 5000
        sheet.col(2).width = 5000
        sheet.col(3).width = 5000
        sheet.col(4).width = 4500
        sheet.col(5).width = 4000
        sheet.col(6).width = 3000
        sheet.col(7).width = 3000
        sheet.col(8).width = 5000

        # Write header
        sheet.write_merge(0, 0, 0, 8, f'({self.start_date})/({self.end_date}) Fuel Inventory (عهدة الوقود)', main_heading)
        sheet.write(1, 0, "التاريخ", heading)
        sheet.write(1, 1, "رقم العهدة", heading)
        sheet.write(1, 2, "اسم المستلم", heading)
        sheet.write(1, 3, "المبلغ المسلم(العهدة)", heading)
        sheet.write(1, 4, "المبلغ المصروف", heading)
        sheet.write(1, 5, "الرصيد المتبقي", heading)
        sheet.write(1, 6, "نوع الحركة", heading)
        sheet.write(1, 7, "المرجع", heading)
        sheet.write(1, 8, "البيان", heading)
     
        requests = []
        custody_amount = 0
        expenses_amount = 0
        row = 2
        payment_requests = self.env['payment.request'].search([ 
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
            ('state', 'in', ['paid','close']),
            ('is_need_clearance', '=', True),
        ], order='date asc, id asc')
        paymentrequests = self.env['payment.request'].search([
            ('state', 'in', ['paid', 'close']),
        ])
        
        print("Total =", len(paymentrequests))
        print("Total =", len(payment_requests))
        sheet.write(2, 0, len(paymentrequests), content_format)
        sheet.write(3, 0, len(payment_requests), content_format)
        row = 4
        

        for payment_request in payment_requests:
            if requests==[]:
                ref="رصيد افتتاحي"
            else:
                ref="تجديد العهدة"
            requests.append(payment_request.name)
            sheet.row(row).height = 400
            sheet.write(row, 0, payment_request.date.strftime('%d/%m/%Y'), content_format)
            sheet.write(row, 1, payment_request.name, content_format)
            sheet.write(row, 2, payment_request.employee_id.name, content_format)
            sheet.write(row, 3, payment_request.amount, content_format)
            sheet.write(row, 4, "-", content_format)
            sheet.write(row, 5, payment_request.base_amount, content_format)
            sheet.write(row, 6, "استلام", content_format1)
            sheet.write(row, 7, "-" , content_format)
            sheet.write(row, 8, ref, content_format)
            custody_amount +=payment_request.amount
            row += 1
            clearances = self.env['custody.clearance'].search([
                ('date', '>=', self.start_date),
                ('date', '<=', self.end_date),
                ('state', '=', 'done'),
                ('request_id', '=', payment_request.id),
            ], order='date asc, id asc')
            for clearance in clearances:           
                sheet.row(row).height = 400
                sheet.write(row, 0, clearance.date.strftime('%d/%m/%Y'), content_format)
                sheet.write(row, 1, clearance.sequence, content_format)
                sheet.write(row, 2, clearance.employee_id.name, content_format)
                sheet.write(row, 3, "-", content_format)
                sheet.write(row, 4, clearance.total_amount, content_format)
                sheet.write(row, 5, clearance.request_remaining_amount, content_format)
                sheet.write(row, 6, "صرف", content_format2)
                sheet.write(row, 7, "-", content_format)
                sheet.write(row, 8, clearance.custody_line_ids.desc, content_format)
                expenses_amount += clearance.total_amount
                row += 1
                new_row= row
                rema_amount = custody_amount - expenses_amount
 
        sheet.row(new_row).height = 400
        sheet.write(new_row, 0, "المجموع", heading)
        sheet.write(new_row, 1, "-", heading)
        sheet.write(new_row, 2, "-", heading)
        sheet.write(new_row, 3, custody_amount, heading)
        sheet.write(new_row, 4, expenses_amount, heading)
        sheet.write(new_row, 5, "-", heading)
        sheet.write(new_row, 6, row-2, heading)
        sheet.write(new_row, 7, row-2, heading)
        sheet.write(new_row, 8, "-", heading)
        new_row+= 1
        # Save to stream and encode
        sheet.row(new_row).height = 400
        sheet.write(new_row, 0,)
        sheet.write(new_row, 1,)
        sheet.write(new_row, 2,)
        sheet.write(new_row, 3, rema_amount, content_format3)
        sheet.write(new_row, 4, "", content_format3)
        sheet.write(new_row, 5,)
        sheet.write(new_row, 6,)
        sheet.write(new_row, 7,)
        sheet.write(new_row, 8,)

    
        stream = BytesIO()
        workbook.save(stream)
        out = base64.encodebytes(stream.getvalue())

        # Create attachment
        attachment = self.env['ir.attachment'].sudo().create({
            'name': 'clearnce Report.xls',
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
