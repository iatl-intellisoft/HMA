# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request

class ValidateBid(http.Controller):
    @http.route(['/rfq_comparison_chart/purchase_rfq/<model("bid.evaluation"):bid>'], type='http', auth='public', website=True)
    def purchase_comparison(self, bid, **post):
        supplier_ids = []; product_ids=[]; qty_currency=[];values = []; amt = []; number = [] ; supplier_id = [] ;  
        counts = 1
        po = False
        print("materialllllllllllllllllllllll",bid.id)
        for record in request.env['contract.rfq'].sudo().search([('request_id', '=',bid.contract_request.id)]):
            print("reccccccccccccccccccccccccccccccc")
            po = record
            # Append supplier
            supplier_ids.append({'supplier_id':record.subcontractor_name.id, 'sname':record.subcontractor_name.name})
            supplier_id.append(record.subcontractor_name.id)
            number.append(counts)
            # qty_currency.append(record.currency_id)
            # Append Products and quantity
            counts +=1
            for line in record.rfq_line_ids:
                if values:
                    if line.service_description not in product_ids:
                        product_ids.append(line.service_description)
                        values.append({'service_description':line.service_description,'currency_id':line.currency_id.name, 'quantity':line.quantity, 'price_unit':line.price_unit, 'total_price':line.total_price})
                else:
                    product_ids.append(line.service_description)
                    values.append({'service_description':line.service_description,'currency_id':line.currency_id.name, 'quantity':line.quantity, 'price_unit':line.price_unit, 'total_price':line.total_price})
        print("cont valueeeeeeeeee111",values)
        count = 0; reson='';project_name='';date='';TECHNICAL_SCORE =[];payment_term = [];TECHNICAL_KNOWLEDGE =[];AVAILABILITY = [] ;DURATION = [];PREVIOUS = [];Warranties = [];recommended_bidder_ids=[];remark=''; supplier_amount_total = [];service = []; landed_cost_service = []; rfq_currency_to_bid_cureency=[];discount=[]; payment_term=[];delevery_point =[]; delevery_time=[];no_of_col = 2 ; even_number = [] ; bid_currecy = '' ;odd_number = []
        reson = bid.resone
        remark = bid.remarks
        project_name = bid.project_name
        date = bid.date
        for vendor in bid.recommended_bidder_ids:
            recommended_bidder_ids.append(vendor.name)
            print("veeeeeeeeeeeeeeeee",recommended_bidder_ids)

        
       
        
        

        # Append amount based on the products and supplier
        for separate_values in values:
            for suppliers in supplier_ids:
                print("supplier",suppliers)
                print("111111111111111111111",request.env['contract.rfq'].sudo().search([('request_id', '=',bid.contract_request.id),('subcontractor_name', '=',suppliers['supplier_id'])]))
                for record in request.env['contract.rfq'].sudo().search([('request_id', '=',bid.contract_request.id),('subcontractor_name', '=',suppliers['supplier_id'])]):
                    print("2222222222222",request.env['contract.rfq.line'].search([('rfq_id', '=', record.id),('service_description', '=',separate_values['service_description'])]))

                    for po_line in request.env['contract.rfq.line'].search([('rfq_id', '=', record.id),('service_description', '=',separate_values['service_description'])]):
                        amt.append({'currency_id':po_line.currency_id, 'quantity':po_line.quantity,'price_unit':po_line.price_unit,'total_price':po_line.total_price})
        

            values[count]['amt'] = amt
            count +=1
            amt = []
        print("cont valueeeeeeeeeeeeeeeeeeeeeeeeee2222",values)
        # Generate number to create rows and columns
        total_supplier = len(number)
        if total_supplier >= 2:
            increase_by_supplier = total_supplier * no_of_col
        else:
            increase_by_supplier = no_of_col
        if total_supplier > 1:
            total_no = range(1, increase_by_supplier + 1)
            supplier_amount_total_1 = list(range(1, increase_by_supplier + 1))
        else:
            total_no = range(1, increase_by_supplier)
            supplier_amount_total_1 = list(range(1, increase_by_supplier))
        for c_number in total_no:
            if c_number%2 ==0:
                even_number.append(c_number)
            else:
                odd_number.append(c_number)
      
        for record in request.env['contract.rfq'].sudo().search([('request_id', '=',bid.contract_request.id)]):
            if record.payment_term:
                payment_term.append(record.payment_term)
            TECHNICAL_KNOWLEDGE.append(record.technical_knowledge)
            AVAILABILITY.append(record.availability_of_equipment_and_tools)
            DURATION.append(record.duration_of_Work)
            PREVIOUS.append(record.previous_performance_with_ram)
            Warranties.append(record.warranties)
            TECHNICAL_SCORE.append(record.technical_score)
        print("paaaaaaaaaa============================",payment_term)



            

        #     state=[]
        #     supplier_amount_total.append(record.amount_total)
        #     discount.append(record.ks_amount_discount)
        #     payment_term.append(record.payment_term_id)
        #     delevery_point.append(record.Delivery_point)
        #     delevery_time.append(record.delivery_time)
        #     print("paaaaaaaaaa",payment_term)
        #     equivalent_currency = bid.equivalent_currency
        #     if equivalent_currency:
        #         currency = bid.currency_rate.filtered(lambda r: r.currency_id == equivalent_currency)
        #         if currency:
        #             curency_rate =currency.rate
        #             bid_currecy = 'Equivalent in' + currency.currency_id.name
        #             po_currnecy_to_bid_currency =record.amount_total * curency_rate
        #             rfq_currency_to_bid_cureency.append(po_currnecy_to_bid_currency)


            # for cost_line in record.landed_cost_line_ids:
            #     state.append(cost_line.states)
            # vals={'state':state}
            # landed_cost_service.append(vals)

            
        # Update the amount in even number position
        tcount = 1    
        # for i in even_number:        
        #     supplier_amount_total_1[i-1] = supplier_amount_total[tcount-1]
        #     tcount +=1
        # Update the supplier id in odd number position
        scount = 1
        for odd_no in odd_number:
            for total in total_no:
                if total == odd_no:                  
                    supplier_amount_total_1[odd_no-1] = supplier_id[scount-1]
                    scount +=1
        return request.render('contract_ram.purchase_comparison', {'data':values,'AVAILABILITY':AVAILABILITY,'DURATION':DURATION,'Warranties':Warranties,'TECHNICAL_SCORE':TECHNICAL_SCORE,'PREVIOUS':PREVIOUS,'supplier':supplier_ids,'purchase_requisition_id':bid,
                                                               'number':number, 'to_no':total_no,'column_no':even_number,'TECHNICAL_KNOWLEDGE':TECHNICAL_KNOWLEDGE,'payment_term':payment_term, 'supplier_amount_total':supplier_amount_total,
                                                                'supplier_amount_total_1':supplier_amount_total_1, 'odd_number':odd_number,'project_name':project_name,'date':date,'reson':reson,'remark':remark,'recommended_bidder_ids':recommended_bidder_ids})



