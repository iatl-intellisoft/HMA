# -*- coding: utf-8 -*-

from odoo import models, fields


class SaleReportPaymentLine(models.TransientModel):
    """One record per reconciled payment for a sales report line."""
    _name = 'sale.report.payment.line'
    _description = 'Sales Report Payment Detail'

    line_id = fields.Many2one(
        'sale.report.line',
        string='Report Line',
        required=True,
        ondelete='cascade',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='line_id.currency_id',
        store=True,
    )
    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        readonly=True,
    )
    bank_reference = fields.Char(string='Bank Reference', readonly=True)


class SaleReportLine(models.TransientModel):
    _name = 'sale.report.line'
    _description = 'Sales Details Report Line'
    _order = 'invoice_date asc, id asc'

    wizard_id = fields.Many2one(
        'sale.report.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    move_id = fields.Many2one('account.move', string='Invoice', readonly=True)

    # ── Descriptive columns ───────────────────────────────────────────────────
    sale_order_ref = fields.Char(string='Sale Order Ref', readonly=True)
    invoice_date = fields.Date(string='Invoice Date', readonly=True)
    salesperson_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)

    # ── Monetary columns ──────────────────────────────────────────────────────
    total_discount = fields.Monetary(
        string='Total Discount',
        currency_field='currency_id',
        readonly=True,
    )
    invoice_total = fields.Monetary(
        string='Invoice Total',
        currency_field='currency_id',
        readonly=True,
    )
    refund_total = fields.Monetary(
        string='Refunds Total',
        currency_field='currency_id',
        readonly=True,
    )
    net_total = fields.Monetary(
        string='Net Total',
        currency_field='currency_id',
        readonly=True,
    )
    paid = fields.Monetary(
        string='Paid',
        currency_field='currency_id',
        readonly=True,
    )
    net = fields.Monetary(
        string='Net',
        currency_field='currency_id',
        readonly=True,
    )
    bank_reference = fields.Char(
        string="Bank Transaction Number"
    )

    # ── Per-payment breakdown ─────────────────────────────────────────────────
    payment_line_ids = fields.One2many(
        'sale.report.payment.line',
        'line_id',
        string='Payment Details',
        readonly=True,
    )
