# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CheckPrintingReason(models.Model):
    _name = "check.printing.log"
    _description = 'Check Printing Log'
    _order = 'print_date desc, id desc'

    payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        ondelete='set null',
        readonly=True,
    )
    reason_id = fields.Many2one(
        'check.printing.reason',
        string='Reason',
        ondelete='set null',
        readonly=True,
    )
    check_no = fields.Integer(string='Check No', readonly=True)
    beneficiary = fields.Char(string='Beneficiary', readonly=True)
    print_date = fields.Datetime(
        string='Print Date',
        readonly=True,
        default=fields.Datetime.now,
        help="Date and time when the check was printed.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('payment_id'):
                payment = self.env['account.payment'].browse(vals['payment_id'])
                if payment.exists():
                    vals['beneficiary'] = payment.beneficiary
            if not vals.get('print_date'):
                vals['print_date'] = fields.Datetime.now()
        return super().create(vals_list)

    @api.depends('payment_id', 'check_no')
    def _compute_display_name(self):
        for record in self:
            payment_name = record.payment_id.name or ''
            check_no = str(record.check_no or '')
            record.display_name = '%s / %s' % (payment_name, check_no)
