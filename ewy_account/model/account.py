from odoo import api, fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    second_currency_id = fields.Many2one('res.currency', string='2nd Currency')

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        for rec in self:
            if not rec.second_currency_id:
                rec.second_currency_id = rec.currency_id
