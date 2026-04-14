from odoo import models, fields, api
from odoo.exceptions import ValidationError 

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    manual_account_id = fields.Many2one(
        'account.account',
        string='Manual Account', 
    )

    @api.constrains('partner_id', 'manual_account_id')
    def _check_partner_or_account(self):
        for rec in self:
            if not rec.partner_id and not rec.manual_account_id:
                raise ValidationError("يجب إختيار عميل أو حساب")
            if rec.partner_id and rec.manual_account_id:
                raise ValidationError(" إختيار عميل وعميل في نفس الوقت غير مسموح به")
    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        res = super()._prepare_move_line_default_vals(write_off_line_vals)

        for line in res: 
            if not self.partner_id and self.manual_account_id:
                if line.get('manual_account_id') == self.destination_manual_account_id.id:
                    line['manual_account_id'] = self.manual_account_id.id

        return res      
# class SaleOrder(models.Model):
#     _inherit = 'sale.order'
    
#     def action_register_payment(self):
#         self.ensure_one()

         
#         invoices = self.invoice_ids.filtered(
#             lambda inv: inv.state == 'posted' and inv.payment_state != 'paid'
#         )

#         if not invoices:
#             raise UserError("لا توجد فواتير متاحة للسداد (قد تكون مدفوعة أو قيد التسوية)")

#         return {
#             'type': 'ir.actions.act_window',
#             'name': 'Register Payment',
#             'res_model': 'account.payment.register',
#             'view_mode': 'form',
#             'target': 'new',
#             'context': {
#                 'active_model': 'account.move',
#                 'active_ids': invoices.ids,
#             },
#         }

