from odoo import models, fields, api
from odoo.exceptions import UserError

class ShippingDestination(models.Model):
    _name = 'shipping.destination'
    _description = 'shipping destination'
     
    code = fields.Integer(string="Code")
    name = fields.Char(string="City Name")

   
class SaleOrder(models.Model):
    _inherit = 'sale.order'

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

    shipping_office_name = fields.Char(related='sale_id.shipping_office_name', store=True)
    shipping_office_number = fields.Char(related='sale_id.shipping_office_number', store=True)
    shipping_destination = fields.Many2one('shipping.destination', string="مكان ارسال البضاعة", store=True)
    

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    shipping_receipt = fields.Binary(string="ايصال الشحن")
    shipping_receipt_name = fields.Char(string="اسم الملف")