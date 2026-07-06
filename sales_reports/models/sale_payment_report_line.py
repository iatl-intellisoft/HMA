# -*- coding: utf-8 -*-

from odoo import models, fields


class SalePaymentReportLine(models.TransientModel):
    _name = 'sale.payment.report.line'
    _description = 'Payment Details Report Line'
    _order = 'sequence asc'

    wizard_id = fields.Many2one(
        'sale.payment.report.wizard',
        required=True,
        ondelete='cascade',
    )
    currency_id = fields.Many2one(
        related='wizard_id.currency_id',
        string='Currency',
        readonly=True,
    )

    # ── Report columns ────────────────────────────────────────────────────────
    sequence = fields.Integer(string='Seq', readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)

    invoices_total = fields.Monetary(
        string='Invoices Total',
        currency_field='currency_id',
        readonly=True,
    )
    cash_total = fields.Monetary(
        string='Cash Total',
        currency_field='currency_id',
        readonly=True,
    )
    cheque_total = fields.Monetary(
        string='Cheques Total',
        currency_field='currency_id',
        readonly=True,
    )
    transfer_total = fields.Monetary(
        string='Transfers Total',
        currency_field='currency_id',
        readonly=True,
    )
    difference = fields.Monetary(
        string='Difference',
        currency_field='currency_id',
        readonly=True,
    )
