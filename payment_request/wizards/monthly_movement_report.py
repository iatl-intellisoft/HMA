import base64
from io import BytesIO
from locale import currency

import xlwt
import xlsxwriter
from odoo import fields, api, models, _
from odoo.exceptions import ValidationError


class MonthlyMovementReport(models.TransientModel): 
    _name = 'monthly.movement.report'
    _description = __doc__

    start_date = fields.Date()
    end_date = fields.Date()

    @api.constrains('start_date', 'end_date')
    def _check_monthly_movement_report_date_check(self):
        """Check if end date is after start date"""
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_("End date cannot be earlier than start date."))

    def action_generate_monthly_movement_excel(self):
        """Generate and return Excel file for monthly movement"""
        
        workbook = xlwt.Workbook(encoding='utf-8') 
        sheet = workbook.add_sheet('GPS', cell_overwrite_ok=True)

        sheet.cols_right_to_left = True 

 
        title_style = xlwt.easyxf("""
            font: bold 1, height 320;
            align:  wrap on, horiz center, vert center;
            pattern: pattern solid, fore_colour gray25;
            borders: left thin, right thin, top thin, bottom thin;
        """)

        header_style = xlwt.easyxf("""
            font: bold 1;
            align:  wrap on, horiz center, vert center;
            pattern: pattern solid, fore_colour light_green;
            borders: left thin, right thin, top thin, bottom thin;
        """)

        cell_style = xlwt.easyxf("""
            align:  wrap on, horiz center, vert center;
            borders: left thin, right thin, top thin, bottom thin;
        """)

        number_style = xlwt.easyxf("""
            align:  wrap on, horiz center, vert center;
            borders: left thin, right thin, top thin, bottom thin;
        """, num_format_str='#,##0.00')

        total_style = xlwt.easyxf("""
            font: bold 1;
            align:  wrap on, horiz center, vert center;
            pattern: pattern solid, fore_colour ice_blue;
            borders: left thin, right thin, top thin, bottom thin;
        """, num_format_str='#,##0.00') 

        truck_odometers = self.env['fleet.vehicle.odometer'].search([
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
        ])

        data = {}

        for rec in truck_odometers:
            month = rec.date.strftime('%Y-%m')
            plate = rec.vehicle_id.license_plate

            data.setdefault(month, {})
            data[month].setdefault(plate, [])
            data[month][plate].append(rec.value)
 
        result = {}
        all_trucks = set()
        sheet.col(0).width = 5000
        sheet.col(1).width = 4000
        sheet.col(2).width = 4000
        sheet.col(3).width = 4000

        for month, trucks in data.items():
            result[month] = {}
            for plate, values in trucks.items():
                distance = max(values) - min(values)
                result[month][plate] = distance
                all_trucks.add(plate)

        all_trucks = sorted(all_trucks)
 
        sheet.write_merge(1, 1, 1, 9,
                        'Monthly Movement (حركة الدفارات الشهرية مع GPS)',
                        title_style)
 
        sheet.write(3, 0, 'التاريخ', header_style)

        col = 1
        for truck in all_trucks:
            truck_driver = self.env['fleet.vehicle'].search([
                ('license_plate', '=', truck)
            ])
            name=truck+" ( "+truck_driver.driver_id.name+" )"
            sheet.write(3, col, name, header_style)
            col += 1

        sheet.write(3, col, 'اجمالي كل الشهر', header_style)
 
        row = 4
        monthly_totals = {t: 0 for t in all_trucks}
        grand_total = 0

        for month in sorted(result.keys()):
            sheet.write(row, 0, month, cell_style)

            col = 1
            month_total = 0

            for truck in all_trucks:
                value = result[month].get(truck, 0)
                sheet.write(row, col, value, number_style)

                monthly_totals[truck] += value
                month_total += value

                col += 1

            sheet.write(row, col, month_total, number_style)
            grand_total += month_total

            row += 1
 
        sheet.write(row, 0, 'اجمالي المسافة المقطوعة (كم)', header_style)

        col = 1
        for truck in all_trucks:
            sheet.write(row, col, monthly_totals[truck], total_style)
            col += 1

        sheet.write(row, col, grand_total, total_style)
       
        stream = BytesIO()
        workbook.save(stream)
        out = base64.encodebytes(stream.getvalue())
        # Create attachment
        attachment = self.env['ir.attachment'].sudo().create({
            'name': f'monthly movement({self.start_date})/({self.end_date}) Report.xls',
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
