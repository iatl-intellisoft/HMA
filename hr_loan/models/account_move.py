from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    payment_id = fields.Many2one("loan.payment", string="Loan Payment", required=False, )

    def _post(self, soft=True):
        rec = super()._post(soft)
        payment_line = self.env['loan.payment'].search([('id', '=', self.payment_id.id)])
        if payment_line:
            payment_line.write({'state': 'paid'})
            for line in payment_line.loan_line_ids:
                line.action_paid_amount()
        return rec

# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'
#
#     payment_id = fields.One2many("loan.payment", string="Loan Payment", required=False, )
