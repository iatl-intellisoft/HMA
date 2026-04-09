from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    bankak_transaction_number = fields.Char(string="رقم العملية", copy=False)
    bank_transaction_notification = fields.Binary(string="اشعار العملية")

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
