from odoo import models, fields, api
from odoo.exceptions import UserError

class ShippingDestination(models.Model):
    _name = 'shipping.destination'
    _description = 'shipping destination'
     
    code = fields.Integer(string="Code")
    name = fields.Char(string="City Name")

class AccountPayment(models.Model):
    _inherit = 'account.payment' 

    bankak_transaction_number = fields.Char(string="رقم المعاملة البنكية")  
    bank_transaction_notification = fields.Binary(string="الإشعار البنكي")



    @api.constrains('bankak_transaction_number')
    def _check_duplicate_bankak_number(self):
        for rec in self:
            if rec.bankak_transaction_number:
                existing = self.search([
                    ('bankak_transaction_number', '=', rec.bankak_transaction_number),
                    ('id', '!=', rec.id)
                ], limit=1)
                
                if existing:
                    raise ValidationError(
                        "لقد تم تحويل مبلغ بنفس رقم العملية!"
                    )  
  
class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    bankak_transaction_number = fields.Char(string="رقم المعاملة البنكية")
    bank_transaction_notification = fields.Binary(string="الإشعار البنكي")

    def _create_payments(self):
        payments = super()._create_payments()

        for payment in payments:
            payment.bankak_transaction_number = self.bankak_transaction_number
            payment.bank_transaction_notification = self.bank_transaction_notification 

        return payments
class SaleOrder(models.Model):
    _inherit = 'sale.order'  
    
    has_beneficiary = fields.Boolean(
        string="لمستفيد اخر"
    )

    beneficiary_id = fields.Many2one(
        "res.partner",
        string="المستفيد"
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
    
    has_beneficiary = fields.Boolean(
        string="لمستفيد اخر"
    )

    beneficiary_id = fields.Many2one(
        "res.partner",
        string="المستفيد"
    )
    truck_id = fields.Many2one('fleet.vehicle' , string="Truck" )
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

