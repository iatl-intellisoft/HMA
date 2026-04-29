import base64
from io import BytesIO
from locale import currency
from collections import defaultdict

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
        truck_odometers = self.env['fleet.vehicle.odometer'].search([
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
        content_format4 = xlwt.easyxf('align:horiz center,  vert center; font: height 250;pattern:pattern solid,fore_colour light_blue;',num_format_str="#,##0.00")
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
        sheet.col(6).width = 4000
        sheet.col(7).width = 4000
        sheet.col(8).width = 4000
        sheet.col(9).width = 4000
        sheet.col(10).width = 4000
        sheet.col(11).width = 4000
        sheet.col(12).width = 4000

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
        
        pickings = self.env['stock.picking'].search([ 
            ('scheduled_date', '>=', self.start_date),
            ('scheduled_date', '<=', self.end_date), 
            ('truck_id', '!=', False)])
         
        all_picking = 0
        picking_done = 0
        picking_not_done = 0        

        result = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'amount': 0, 'all_amount': 0}))
        result1 =  defaultdict(lambda: defaultdict(lambda: { 'all_amount': 0}))
        all_result = defaultdict(lambda: {'count': 0})
        all_result_not_done = defaultdict(lambda: {'count': 0})

        total = defaultdict(float)
        result_total = 0
        total_per_month = defaultdict(float)
        total_per_truck = defaultdict(float)
        all_delivery_amount = defaultdict(lambda: {'amount': 0})

        for picking in pickings: 
            truck = picking.truck_id.name
            month = picking.scheduled_date.strftime('%Y-%m')
            if picking.state == 'done':
                result[month][truck]['count'] += 1
                all_result[month]['count'] += 1

                result[month][truck]['amount'] += picking.delivery_amount
                all_delivery_amount[month]['amount'] += picking.delivery_amount
                
                result[truck]['all_amount'] = result[month][truck]['amount']
                result_total += picking.delivery_amount 
                
            else:
                all_result_not_done[month][truck]['count'] += 1
                all_result_not_done[month]['count'] += 1




        truck_odometer={}
        for rec in truck_odometers:
            # if rec.state == "paid":    
            if rec.vehicle_id.license_plate not in truck_odometer:
                truck_odometer[rec.vehicle_id.license_plate]={
                            'license_plate': rec.vehicle_id.license_plate,
                            'odometer':[],
                            'distance' : 0, 
                            'days':[],
                    }
            truck_odometer[rec.vehicle_id.license_plate]['odometer'].append(rec.value)
            max_odometer = max(truck_odometer[rec.vehicle_id.license_plate]['odometer'])
            min_odometer = min(truck_odometer[rec.vehicle_id.license_plate]['odometer'])
            distance = max_odometer - min_odometer
            if rec.date not in truck_odometer[rec.vehicle_id.license_plate]['days']:
                truck_odometer[rec.vehicle_id.license_plate]['days'].append(rec.date)

            truck_odometer[rec.vehicle_id.license_plate]['distance'] = distance 
        
        

                
        operating_cost = {} 
        maintenance_cost = {}  
        all_operating_cost_monthly = defaultdict(lambda: {'cost': 0})
        for rec in operating_costs:
            if rec.state == "paid":
                month = rec.date.strftime('%Y-%m')                
                if rec.vehicle_id.license_plate not in operating_cost:
                    operating_cost[rec.vehicle_id.license_plate]={
                            'cost':0,
                        }
                operating_cost[rec.vehicle_id.license_plate]['cost']+=rec.total_amount
                operating_cost[rec.vehicle_id.license_plate][month]['cost']+=rec.total_amount
                all_operating_cost_monthly[month]['cost']+= rec.total_amount
                if rec.custody_type in ['maintenance','oil_change','car_tire_repair']:
                    if rec.vehicle_id.license_plate not in maintenance_cost:
                        maintenance_cost[rec.vehicle_id.license_plate]={
                                'maintenance_cost':0,
                            }
                    maintenance_cost[rec.vehicle_id.license_plate]['maintenance_cost']+=rec.total_amount
 
                
        # Write data rows
        row = 2
        custodys = []
        vehicles = {}
        custody_amount = 0
        expenses_amount = 0 
        months=[]
        all_vehicles = defaultdict(lambda: {'amount': 0})

        for rec in records: 
            if rec.state == "done":   
                month = rec.date.strftime('%Y-%m')
                if month not in months:
                    months.append(month)
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
                all_vehicles[month]['amount']+=rec.custody_line_ids.amount

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
        sheet.write_merge(9, 9, 0, 12, f'مؤشرات تقييم الاداء الشهري لحركة وتشغيل الدفارات للفترة ({self.start_date})الي({self.end_date})', main_heading)

        row+=1
        
        sheet.row(row).height = 1200 
        sheet.write(row, 0, "رقم الدفار", heading)
        sheet.write(row, 1, "اسم السائق", heading)
        sheet.write(row, 2, "اجمالي اللترات", heading)
        sheet.write(row, 3, "اجمالي تكلفة الوقود", heading)
        sheet.write(row, 4, "اجمالي تكلفة الصيانة لكل دفار", heading)
        sheet.write(row, 5, "اجمالي تكلفة مصروفات التشغيل لكل دفار", heading)
        sheet.write(row, 6, "عداد الكيلو", heading)
        sheet.write(row, 7, "معدل الكفاءة والاستهلاك (كم/لتر)", heading)
        sheet.write(row, 8, "نسبة التشغيل الزمني", heading)
        sheet.write(row, 9, "نسبة التشغيل الفعلي", heading)
        sheet.write(row, 10, "تكلفة الصيانة لكل كيلومتر", heading)
        sheet.write(row, 11, "نسبة استهلاك الوقود من الميزانية", heading)
        sheet.write(row, 12, "نسبة استهلاك مصروفات التشغيل من الميزانية", heading)
        
        new_row=row
        num_row=0
        all_fuel=0
        all_fuel_cost=0
        all_operating_cost=0
        all_distance=0
        all_maintenance_cost=0
        all_maintenance_cost_distance=0
        all_vehicle_sale = 0
        all_fuel_cost_truck={}
        fuel_amount = []
        operation_cost_amount = []
        sum_days = 0
        sum_days_income = 0
        for vehicle, data in vehicles.items():  
            row+=1 
            num_row+=1
            license_plate=data['license_plate']            
            truck=self.env['fleet.vehicle'].search([
                ('license_plate', '=', license_plate), 
            ],)
            truck = truck.name
            name = data['name']  
            if license_plate in truck_odometer :
                distance=truck_odometer[license_plate]['distance']  
            else:
                distance =0
            days = truck_odometer.get(license_plate, {}).get('days', 0)
            if days != 0:
                days = len(days)
            days = days / 26 * 100
            
            fuel_amount.append(data['amount'])
            sum_days += days
            if result_total != 0:
                sum_days_income += result.get(truck, {}).get('all_amount', 0) / result_total * 100
            operation_cost_amount.append(operating_cost.get(license_plate, {}).get('cost', 0))
            sheet.write(row, 0, data['license_plate'], content_format)
            sheet.write(row, 1, data['driver'], content_format)
            sheet.write(row, 2, data['fuel'], content_format)
            sheet.write(row, 3, data['amount'], content_format)
            sheet.write(row, 4, maintenance_cost.get(license_plate, {}).get('maintenance_cost', 0), content_format  )
            sheet.write(row, 5, operating_cost.get(license_plate, {}).get('cost', 0), content_format  )
            sheet.write(row, 6, distance ,content_format) 
            sheet.write(row, 7, data['fuel']/distance if distance > 0 else 0.0  , content_format)
            sheet.write(row, 8, f'{"{:.2f}".format(days)}%' , content_format)
            sheet.write(row, 9, f'{"{:.2f}".format(result.get(truck, {}).get('all_amount', 0) / result_total * 100) }%' if result_total != 0 else 0, content_format)
            sheet.write(row, 10, f'{"{:.2f}".format(maintenance_cost.get(license_plate, {}).get('maintenance_cost', 0) / distance )}' if distance != 0 else 0, content_format)
            # sheet.write(row, 11, f'{"{:.2f}".format(all_fuel_cost / budget * 100) }%' , content_format)
            # sheet.write(row, 12, f'{"{:.2f}".format(operating_cost.get(license_plate, {}).get('cost', 0) / budget * 100) }%', content_format  )
            all_fuel+= data['fuel']
            all_fuel_cost+= data['amount']   
            all_fuel_cost_truck = defaultdict(lambda: {'all_fuel_cost': 0})
            all_fuel_cost_truck[license_plate]['all_fuel_cost'] = data['amount']
            all_maintenance_cost+=maintenance_cost.get(license_plate, {}).get('maintenance_cost', 0)
            all_operating_cost+=operating_cost.get(license_plate, {}).get('cost', 0)
            all_distance+=distance 
            all_maintenance_cost_distance += maintenance_cost.get(license_plate, {}).get('maintenance_cost', 0)/distance if distance > 0 else 0
            total_fuel_cost = sum(
                truck['all_fuel_cost'] for truck in all_fuel_cost_truck.values()
            )
        print(operation_cost_amount)
        print(fuel_amount)
        budget = sum(operation_cost_amount) + sum(fuel_amount)
        print(budget)
        sum_fuel_amount = 0
        sum_operation_cost_amount = 0
        row-=len(fuel_amount)-1   
        for amount in fuel_amount: 
            sheet.write(row, 11, f'{"{:.2f}".format(amount / budget * 100) }%' , content_format)
            sum_fuel_amount += amount / budget * 100
            row+=1
        row=row-len(fuel_amount)
        for amount in operation_cost_amount:  
            sheet.write(row, 12, f'{"{:.2f}".format(amount / budget * 100) }%', content_format)
            sum_operation_cost_amount += amount / budget * 100

            row+=1
        # for vehicle, data in vehicles.items(): 
        #     license_plate=vehicle.license_plate
        #     print(license_plate,all_fuel_cost_truck[license_plate]['all_fuel_cost'],"this is budget = ",budget)
        #     # print(operating_cost.get(license_plate, {}).get('cost', 0),"this is budget = ",budget)

        #     sheet.write(row, 11, f'{"{:.2f}".format(all_fuel_cost_truck[license_plate]['all_fuel_cost'] / budget * 100) }%' , content_format)
        #     sheet.write(row, 12, f'{"{:.2f}".format((operating_cost.get(license_plate, {}).get('cost', 0) )/ budget * 100) }%', content_format  )
        #     row+=1
        sheet.write(row, 0, num_row, content_format4)
        sheet.write(row, 1, '-', content_format4)
        sheet.write(row, 2, all_fuel, content_format4)
        sheet.write(row, 3, sum(fuel_amount), content_format4)
        sheet.write(row, 4, all_maintenance_cost, content_format4  )
        sheet.write(row, 5, sum(operation_cost_amount), content_format4  )
        sheet.write(row, 6, all_distance ,content_format4)
        sheet.write(row, 7, all_fuel/all_distance if all_distance > 0 else 0 , content_format4)
        sheet.write(row, 8, f'{"{:.2f}".format(sum_days)}%', content_format4)
        sheet.write(row, 9, f'{"{:.2f}".format(sum_days_income)}%', content_format4)
        sheet.write(row, 10, all_maintenance_cost_distance, content_format4)
        sheet.write(row, 11, f'{"{:.2f}".format(sum_fuel_amount)}%', content_format4)
        sheet.write(row, 12, f'{"{:.2f}".format(sum_operation_cost_amount)}%', content_format4)
        row+=3
        sheet.row(row).height = 1200 
        sheet.write(row, 0, "الشهر", heading)
        sheet.write(row, 1, month, heading)
        sheet.write(row, 2, "الميزانية التقديرية الشهرية", heading)
        sheet.write(row, 3, all_operating_cost_monthly[month]['cost']+all_vehicles[month]['amount'], heading) 
        row+=1

        sheet.write(row, 0, "رقم الدفار", content_format4) 
        sheet.write(row, 1, "اسم السائق", content_format4) 
        sheet.write(row, 2, "-", content_format4)  
        sheet.write(row, 3, "تكلفة الوقود الشهري", heading) 
        sheet.write(row, 4, "مصروفات التشغيل الشهرية", heading)
        sheet.write(row, 5, "تكلفة التشغيل الشهرية", heading)
        sheet.write(row, 6, "تكلفة التشغيل اليومية", heading)
        sheet.write(row, 7, "الإيراد التشغيلي الشهري المحقق", heading)
        sheet.write(row, 8, "الإيراد التشغيلي اليومي المحقق", heading)
        sheet.write(row, 9, "نسبة تكلفة التشغيل للشهر", heading)
        sheet.write(row, 10, "نسبة عجز التشغيل", heading)
        sheet.write(row, 11, "عدد الطرود المنجزة", heading)
        sheet.write(row, 12, "نقطة التعادل", heading)
        sheet.write(row, 13, "نسبة الطرود المنجزة", heading) 
        row+=1
        for month in  months :  
            for vehicle, data in vehicles.items(): 
                license_plate=data['license_plate'] 
                truck=self.env['fleet.vehicle'].search([
                    ('license_plate', '=', license_plate), 
                ],)
                sheet.write(row, 0, data['license_plate'], content_format)
                sheet.write(row, 1, data['driver'], content_format)           
                sheet.write(row, 2, "-", content_format)           
                sheet.write(row, 3, "-", content_format)           
                sheet.write(row, 4, "-", content_format)           
                sheet.write(row, 5, operating_cost[license_plate][month]['cost'], content_format4) 
                sheet.write(row, 6, operating_cost[license_plate][month]['cost']/26, content_format4)  
                sheet.write(row, 7, result[month][truck]['amount'], content_format4)  
                sheet.write(row, 8, result[month][truck]['amount']/26, content_format4)  
                sheet.write(row, 9, operating_cost[license_plate][month]['cost']/(all_operating_cost_monthly[month]['cost']+all_vehicles[month]['amount'])*100, content_format4)  
                sheet.write(row, 10, all_result_not_done[month][truck]['count']/(result[month][truck]['count']+all_result_not_done[month][truck]['count'])*100, content_format4)  
                sheet.write(row, 11, result[month][truck]['count'], content_format4)  
                sheet.write(row, 12,"-", content_format4)  
                sheet.write(row, 13, result[month][truck]['count']/(result[month][truck]['count']+all_result_not_done[month][truck]['count'])*100, content_format4)  
                row+=1


            all_picks = all_result_not_done[month]['count'] + all_result[month]['count']
            sheet.write(row, 0, month, content_format4)
            sheet.write(row, 1, "-", content_format4) 
            sheet.write(row, 2, all_operating_cost_monthly[month]['cost']+all_vehicles[month]['amount'], content_format4) 
            sheet.write(row, 3, all_vehicles[month]['amount'], content_format4) 
            sheet.write(row, 4, all_operating_cost_monthly[month]['cost'], content_format4) 
            sheet.write(row, 5, all_operating_cost_monthly[month]['cost']+all_vehicles[month]['amount'], content_format4) 
            sheet.write(row, 6, all_operating_cost_monthly[month]['cost']+all_vehicles[month]['amount']/26, content_format4) 
            sheet.write(row, 7, all_delivery_amount[month]['amount'], content_format4) 
            sheet.write(row, 8, all_delivery_amount[month]['amount']/26, content_format4) 
            sheet.write(row, 9, f'{"{:.2f}".format(all_delivery_amount[month]['amount']/26)}%', content_format4) 
            sheet.write(row, 10,f'{"{:.2f}".format(all_result_not_done[month]['count'] / all_picks * 100)}%' if all_picks > 0 else 0 , content_format4) 
            sheet.write(row, 11, all_result[month]['count'], content_format4)
            sheet.write(row, 12, '', content_format4)
            sheet.write(row, 13, f'{"{:.2f}".format(all_result[month]['count'] / all_picks * 100)}%' if all_picks > 0 else 0, content_format4) 
            row+=1

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
       
 
