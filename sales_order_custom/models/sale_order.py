from odoo import models, fields, api
from odoo.exceptions import UserError

class ShippingDestination(models.Model):
    _name = 'shipping.destination'
    _description = 'shipping destination'
     
    code = fields.Integer(string="Code")
    name = fields.Char(string="City Name")

   
class SaleOrder(models.Model):
    _inherit = 'sale.order'
    truck_id = fields.Many2one('fleet.vehicle', string="Truck")
    driver_id = fields.Many2one(
            'res.partner',
            string="Driver",
            related="truck_id.driver_id",
            store=True,
            readonly=True
        )
    shipping_office_name = fields.Char(string="اسم مكتب الشحن", store=True)
    shipping_office_number = fields.Char(string="رقم مكتب الشحن", store=True)
    shipping_destination = fields.Many2one('shipping.destination', string="مكان ارسال البضاعة", store=True)

   
    def action_confirm(self):
        res = super().action_confirm()

        for order in self: 
            if not order.invoice_ids: 
                invoice = order._create_invoices()
                invoice.action_post()

        return res
    def action_register_payment(self):
        self.ensure_one()

         
        invoices = self.invoice_ids.filtered(
            lambda inv: inv.state == 'posted' and inv.payment_state != 'paid'
        )

        if not invoices:
            raise UserError("لا توجد فواتير متاحة للسداد (قد تكون مدفوعة أو قيد التسوية)")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Register Payment',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'account.move',
                'active_ids': invoices.ids,
            },
        }


  
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    truck_id = fields.Many2one('fleet.vehicle' ,related='sale_id.truck_id', string="Truck" , readonly="1")
    delivery_amount =fields.Integer(string="Delivery Amount")
    driver_id = fields.Many2one(
            'res.partner',
            string="Driver",
            related="truck_id.driver_id",
            store=True,
            readonly=True
        )
    shipping_office_name = fields.Char(related='sale_id.shipping_office_name', store=True)
    shipping_office_number = fields.Char(related='sale_id.shipping_office_number' , store=True)
    shipping_destination = fields.Many2one('shipping.destination', related='sale_id.shipping_destination', string="مكان ارسال البضاعة", store=True)
    shipping_receipt = fields.Binary(string="ايصال الشحن")
    shipping_receipt_name = fields.Char(string="اسم الملف")

    # @api.model
    # def create(self, vals):
    #     if vals.get('sale_id'):
    #         sale = self.env['sale.order'].browse(vals['sale_id'])
    #         if sale.driver_id:
    #             vals['driver_id'] = sale.driver_id.id 

    #     return super().create(vals) 