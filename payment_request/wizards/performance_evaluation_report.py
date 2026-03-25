import base64
from io import BytesIO
from locale import currency

import xlwt
from odoo import fields, api, models, _
from odoo.exceptions import ValidationError


class PerformanceReport(models.TransientModel): 
    _name = 'performance.report'
    _description = __doc__

    start_date = fields.Date()
    end_date = fields.Date()

    @api.constrains('start_date', 'end_date')
    def _check_performance_report_date_check(self):
        """Check if end date is after start date"""
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_("End date cannot be earlier than start date."))

    def action_generate_performance_excel(self):
        """Generate and return Excel file for performance"""
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
        main_heading = xlwt.easyxf('align: wrap on, horiz center, vert center; font: bold True, height 290;pattern:pattern solid,fore_colour light_blue;',num_format_str="#,##0.00")
    
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
        sheet.row(0).height = 600
        sheet.row(1).height = 800
        sheet.row(10).height = 5000

        # Set column widths
        sheet.col(0).width = 6000
        sheet.col(1).width = 6000
        sheet.col(2).width = 5000
        sheet.col(3).width = 5000
        sheet.col(4).width = 5000
        sheet.col(5).width = 5000
        sheet.col(6).width = 3000
        sheet.col(7).width = 3000
        sheet.col(8).width = 3000
        sheet.col(9).width = 4000
        sheet.col(10).width = 4000

        # Write header
        sheet.write_merge(0, 0, 0, 1, 'التقرير الشهري لعهدة الوقود  ', main_heading)
        # sheet.write(1, 0, "التاريخ", heading)
        # sheet.write(1, 1, "رقم العهدة", heading)
        # sheet.write(1, 2, "اسم المستلم", heading)
        # sheet.write(1, 3, "المبلغ المسلم(العهدة)", heading)
        # sheet.write(1, 4, "المبلغ المصروف", heading)
        # sheet.write(1, 5, "الرصيد المتبقي", heading)
        # sheet.write(1, 6, "نوع الحركة", heading)
        # sheet.write(1, 7, "المرجع", heading)
        # sheet.write(1, 8, "البيان", heading)
        truck_odometer={}
        for rec in truck_odometers:
            # if rec.state == "paid":    
            if rec.truck_id.license_plate not in truck_odometer:
                truck_odometer[rec.truck_id.license_plate]={
                            'license_plate': rec.truck_id.license_plate,
                            'odometer':[],
                            'distance' : 0
                    }
            truck_odometer[rec.truck_id.license_plate]['odometer'].append(rec.odometer)
            max_odometer = max(truck_odometer[rec.truck_id.license_plate]['odometer'])
            min_odometer = min(truck_odometer[rec.truck_id.license_plate]['odometer'])
            distance = max_odometer - min_odometer
            truck_odometer[rec.truck_id.license_plate]['distance'] = distance
        print(truck_odometer)
        

                
        operating_cost = {} 
        maintenance_cost = {} 
        for rec in operating_costs:
            if rec.state == "paid":    
                if rec.vehicle_id.license_plate not in operating_cost:
                    operating_cost[rec.vehicle_id.license_plate]={
                            'cost':0,
                        }
                operating_cost[rec.vehicle_id.license_plate]['cost']+=rec.total_amount
                if rec.custody_type in ['maintenance','oil_change','car_tire_repair']:
                    if rec.vehicle_id.license_plate not in maintenance_cost:
                        maintenance_cost[rec.vehicle_id.license_plate]={
                                'maintenance_cost':0,
                            }
                    maintenance_cost[rec.vehicle_id.license_plate]['maintenance_cost']+=rec.total_amount

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
 

        sheet.row(row).height = 400
        sheet.write(row, 0, "البيان", heading)
        sheet.write(row, 1, "المبلغ(جنيه)", heading) 
        row+= 1
        # Save to stream and encode
        sheet.row(row).height = 400
        sheet.write(row, 0,"رصيد افتتاحي", content_format)
        sheet.write(row, 1,base_amount, content_format)
        row+= 1
        sheet.write(row, 0,"اجمالي تجديد العهدة(شهريا)", content_format)
        sheet.write(row, 1,custody_amount, content_format)
        row+= 1
        sheet.write(row, 0,"اجمالي المصروف (شهريا)", content_format)
        sheet.write(row, 1,expenses_amount, content_format)
        row+= 1
        sheet.write(row, 0,"الرصيد الختامي للشهر", main_heading)
        sheet.write(row, 1,rema_amount, main_heading)
        row+= 3 
        sheet.write_merge(9, 9, 0, 10, f'مؤشرات تقييم الاداء الشهري لحركة وتشغيل الدفارات للفترة ({self.start_date}) الي({self.end_date}) (KPIs)', main_heading)

        row+=1
        
        sheet.row(row).height = 1200 
        sheet.write(row, 0, "رقم الدفار", heading)
        sheet.write(row, 1, "اسم السائق", heading)
        sheet.write(row, 2, "اجمالي اللترات", heading)
        sheet.write(row, 3, "اجمالي تكلفة الوقود", heading)
        sheet.write(row, 4, "اجمالي تكلفة الصيانة لكل دفار", heading)
        sheet.write(row, 5, "اجمالي تكلفة التشغيل لكل دفار", heading)
        sheet.write(row, 6, "عداد الكيلو", heading)
        sheet.write(row, 7, "معدل الكفاءة والاستهلاك (كم/لتر)", heading)
        sheet.write(row, 8, "نسبة التشغيل الفعلي", heading)
        sheet.write(row, 9, "تكلفة الصيانة لكل كيلومتر", heading)
        sheet.write(row, 10, "نسبة استهلاك الوقود من الميزانية", heading)
        row+=1 
        num_row=0
        all_fuel=0
        all_fuel_cost=0
        all_operating_cost=0
        all_distance=0
        all_maintenance_cost=0
        all_maintenance_cost_distance=0
        for vehicle, data in vehicles.items():  
            num_row+=1
            license_plate=data['license_plate']
            name = data['name']
            if license_plate in truck_odometer :
                distance=truck_odometer[license_plate]['distance']  
            else:
                distance =0
            sheet.write(row, 0, data['license_plate'], content_format)
            sheet.write(row, 1, data['driver'], content_format)
            sheet.write(row, 2, data['fuel'], content_format)
            sheet.write(row, 3, data['amount'], content_format)
            sheet.write(row, 4,maintenance_cost.get(license_plate, {}).get('maintenance_cost', 0), content_format  )
            sheet.write(row, 5,operating_cost.get(license_plate, {}).get('cost', 0), content_format  )
            sheet.write(row, 6, distance ,content_format) 
            sheet.write(row, 7, data['fuel']/distance if distance > 0 else 0.0  , content_format)
            # sheet.write(row, 7, "نسبة التشغيل الفعلي", heading)
            sheet.write(row, 9, maintenance_cost.get(license_plate, {}).get('maintenance_cost', 0)/distance  if distance > 0 else 0  , content_format)
            # sheet.write(row, 9, "نسبة استهلاك الوقود من الميزانية", heading)
            all_fuel+= data['fuel']
            all_fuel_cost+= data['amount']
            all_maintenance_cost+=maintenance_cost.get(license_plate, {}).get('maintenance_cost', 0)
            all_operating_cost+=operating_cost.get(license_plate, {}).get('cost', 0)
            all_distance+=distance 
            all_maintenance_cost_distance += maintenance_cost.get(license_plate, {}).get('maintenance_cost', 0)/distance if distance > 0 else 0

            row+=1
        sheet.write(row, 0, num_row, main_heading)
        sheet.write(row, 1, '-', main_heading)
        sheet.write(row, 2, all_fuel, main_heading)
        sheet.write(row, 3, all_fuel_cost, main_heading)
        sheet.write(row, 4, all_maintenance_cost, main_heading  )
        sheet.write(row, 5, all_operating_cost, main_heading  )
        sheet.write(row, 6, all_distance ,main_heading)
        sheet.write(row, 7, all_fuel/all_distance, main_heading)
        # sheet.write(row, 7, "نسبة التشغيل الفعلي", heading)
        # sheet.write(row, 8, "تكلفة الصيانة لكل كيلومتر", heading)
        sheet.write(row, 9, all_maintenance_cost_distance, main_heading)
        stream = BytesIO()
        workbook.save(stream)
        out = base64.encodebytes(stream.getvalue())

        # Create attachment
        attachment = self.env['ir.attachment'].sudo().create({
            'name': f'performance({self.start_date})/({self.end_date}) Report.xls', 
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
       