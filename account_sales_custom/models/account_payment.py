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

    destination_account_id = fields.Many2one(
        'account.account',
        compute='_compute_destination_account_id',
        store=True,
        readonly=False
    )

    @api.depends('partner_id', 'manual_account_id')
    def _compute_destination_account_id(self):
        super()._compute_destination_account_id()

        for rec in self:
            if not rec.partner_id and rec.manual_account_id:
                rec.destination_account_id = rec.manual_account_id
