import base64
from io import BytesIO
from locale import currency

import xlwt
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
        records = self.env['custody.clearance'].search([
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
        ])
        operating_costs = self.env['payment.request'].search([ 
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date)
        ])
        truck_odometers = self.env['truck.odometer'].search([
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date), 
        ])

        workbook = xlwt.Workbook(encoding='utf-8')
        sheet = workbook.add_sheet('Clearance', cell_overwrite_ok=True)
        sheet.cols_right_to_left = True
        # Styles
        main_heading = xlwt.easyxf('align: horiz center, vert center; font: bold True, height 290;pattern:pattern solid,fore_colour light_blue;',num_format_str="#,##0.00")
    
        heading = xlwt.easyxf('align: horiz center, vert center; font: height 270;pattern:pattern solid,fore_colour light_green;',num_format_str="#,##0.00")
        content_format = xlwt.easyxf('align:horiz center,  vert center; font: height 220;',num_format_str="#,##0.00")
        content_format1 = xlwt.easyxf('align:horiz center,  vert center; font: height 220; pattern:pattern solid,fore_colour light_green;',num_format_str="#,##0.00")
        content_format2 = xlwt.easyxf('align:horiz center,  vert center; font: height 220;pattern:pattern solid,fore_colour rose;',num_format_str="#,##0.00")
        content_format3 = xlwt.easyxf('align:horiz center,  vert center; font: height 270;pattern:pattern solid,fore_colour red;',num_format_str="#,##0.00")
        currency_format = xlwt.easyxf('align:horiz center, vert center; font: height 220;',num_format_str="#,##0.00")
        # Define styles
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'dd/mm/yyyy'

        # Set row widths
        sheet.row(0).height = 600
        sheet.row(1).height = 800

        # Set column widths
        sheet.col(0).width = 6000
        sheet.col(1).width = 6000
        sheet.col(2).width = 5000
        sheet.col(3).width = 5000
        sheet.col(4).width = 4500
        sheet.col(5).width = 4000
        sheet.col(6).width = 3000
        sheet.col(7).width = 3000
        sheet.col(8).width = 5000

        # Write header
        sheet.write_merge(0, 0, 0, 1, 'التقرير الشهري لعهدة الوقود  ', main_heading)
        truck_monthly_odometer={}
        for rec in truck_odometers:
            # if rec.state == "paid": 
            monthy_key = rec.date.strftime('%Y-%m')   
            if rec.truck_id.license_plate not in truck_monthly_odometer:
                truck_monthly_odometer[rec.truck_id.license_plate]={
                            'license_plate': rec.truck_id.license_plate,
                            'odometer':[],
                            'distance' : 0,
                            'monthy_key':[]
                    }
            truck_monthly_odometer[rec.truck_id.license_plate]['odometer'].append(rec.odometer)
            max_odometer = max(truck_monthly_odometer[rec.truck_id.license_plate]['odometer'])
            min_odometer = min(truck_monthly_odometer[rec.truck_id.license_plate]['odometer'])
            distance = max_odometer - min_odometer
            truck_monthly_odometer[rec.truck_id.license_plate]['distance'] = distance
            if monthy_key not in truck_monthly_odometer[rec.truck_id.license_plate]['monthy_key']:
                truck_monthly_odometer[rec.truck_id.license_plate]['monthy_key'] = 0
            truck_monthly_odometer[rec.truck_id.license_plate]['monthy_key']+=distance
        print(truck_monthly_odometer)
        

                
        operating_cost = {} 
        for rec in operating_costs:
            if rec.state == "paid":    
                if rec.vehicle_id.license_plate not in operating_cost:
                    operating_cost[rec.vehicle_id.license_plate]={
                            'cost':0,
                        }
                operating_cost[rec.vehicle_id.license_plate]['cost']+=rec.total_amount
        print(operating_cost)
                
        # Write data rows
        row = 2
        custodys = []
        vehicles = {}
        custody_amount = 0
        expenses_amount = 0
        for rec in records:
            if rec.state == "done":    
                if rec.vehicle_id not in vehicles:
                    vehicles[rec.vehicle_id]={
                            'vehicle':rec.vehicle_id,
                            'name': rec.vehicle_id.model_id.name,
                            'driver': rec.vehicle_id.driver_id.name,
                            'license_plate': rec.vehicle_id.license_plate,
                            'fuel':0,
                            'amount':0
                        }
                vehicles[rec.vehicle_id]['fuel']+=rec.custody_line_ids.quantity
                vehicles[rec.vehicle_id]['amount']+=rec.custody_line_ids.amount
                print(vehicles)
            if rec.state == "done":          
                if rec.request_id not in custodys:
                    if custodys==[]:
                        ref="رصيد افتتاحي"
                        base_amount = rec.request_id.base_amount
                    else:
                        ref="تجديد العهدة"
                    custodys.append(rec.request_id)
                    custody_amount +=rec.custody_amount
                expenses_amount += rec.total_amount 
                rema_amount = custody_amount - expenses_amount 
      
        sheet.write_merge(9, 9, 0, 9, f'مؤشرات تقييم الاداء الشهري لحركة وتشغيل الدفارات للفترة ({self.start_date}) الي({self.end_date}) (KPIs)', main_heading)
 
        row+=1
        
        sheet.row(row).height = 1200 
        sheet.write(row, 0, "التاريخ", heading)
        col=1
        for truck in truck_monthly_odometer[rec.truck_id.license_plate]:
            sheet.write(row, col, truck_monthly_odometer[rec.truck_id.license_plate], heading)
          
        row+=1 
        for vehicle, data in truck_monthly_odometer.items():  
            num_row+=1 
            truck_monthly_odometer[rec.truck_id.license_plate][monthy_key]['distance']
            sheet.write(row, 0, truck_monthly_odometer[rec.truck_id.license_plate][monthy_key], content_format)
            col=1
            for  monthy_distance in truck_monthly_odometer[rec.truck_id.license_plate][monthy_key]['distance']:
                sheet.write(row, col, monthy_distance, content_format)
                col+=1
            row+=1
        sheet.write(row, 0, "اجمالي المسافة المقطوعة", main_heading)
        stream = BytesIO()
        workbook.save(stream)
        out = base64.encodebytes(stream.getvalue())

        # Create attachment
        attachment = self.env['ir.attachment'].sudo().create({
            'name': f'monthly movement{self.start_date}-{self.end_date} Report.xls',
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