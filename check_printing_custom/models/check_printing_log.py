# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CheckPrintingReason(models.Model):
    _name = "check.printing.log"
    _description = 'Check Printing Log'
    payment_id = fields.Many2one('account.payment', string=u'payment', ondelete='set null', readonly=True)
    reason_id = fields.Many2one('check.printing.reason', string='Reason', ondelete='set null', readonly=True)
    check_no = fields.Integer(string='Check No', readonly=True)
    beneficiary = fields.Char(string="Beneficiary", readonly=True)

    @api.model
    def create(self, vals):
        if vals['payment_id']:
            payment = vals['payment_id']
            beneficiary = self.env['account.payment'].search([('id', '=', payment)])
            vals['beneficiary'] = beneficiary.beneficiary
        return super(CheckPrintingReason, self).create(vals)

    # @api.multi
    def name_get(self):
        res = []
        for record in self:
            payment_id = str(record.payment_id.name)
            check_no = str(record.check_no)
            res.append((record.id, payment_id + ' / ' + check_no))

        return res
