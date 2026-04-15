from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    manual_account_id = fields.Many2one(
        'account.account',
        string='Manual Account'
    )

    @api.constrains('partner_id', 'manual_account_id')
    def _check_partner_or_account(self):
        for rec in self:
            if not rec.partner_id and not rec.manual_account_id:
                raise ValidationError("يجب اختيار عميل أو حساب")

            if rec.partner_id and rec.manual_account_id:
                raise ValidationError("لا يمكن اختيار عميل وحساب يدوي في نفس الوقت")

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        res = super()._prepare_move_line_default_vals(write_off_line_vals)

        if not self.partner_id and self.manual_account_id:
            for line in res:
                if not line.get('partner_id'):
                    line['account_id'] = self.manual_account_id.id

        return res
