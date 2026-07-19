# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class AccountInvoicePaymentReport(models.Model):
    _name = 'account.invoice.payment.report'
    _description = 'تقرير المبيعات مع الدفعات المرتبطة'
    _auto = False
    _order = 'invoice_date desc, move_id, payment_date'

    move_id = fields.Many2one('account.move', string='رقم الفاتورة', readonly=True)
    invoice_date = fields.Date(string='تاريخ الفاتورة', readonly=True)
    partner_id = fields.Many2one('res.partner', string='العميل', readonly=True)
    invoice_origin = fields.Char(string='رقم أمر البيع', readonly=True)
    amount_total = fields.Monetary(string='إجمالي الفاتورة', readonly=True)
    amount_residual = fields.Monetary(string='المتبقي', readonly=True)
    payment_state = fields.Selection(
        [
            ('not_paid', 'غير مدفوعة'),
            ('in_payment', 'قيد الدفع'),
            ('paid', 'مدفوعة'),
            ('partial', 'مدفوعة جزئياً'),
            ('reversed', 'ملغاة'),
            ('invoicing_legacy', 'قديم'),
        ],
        string='حالة السداد', readonly=True,
    )
    move_type = fields.Selection(
        [
            ('out_invoice', 'فاتورة مبيعات'),
            ('out_refund', 'إشعار دائن مبيعات'),
        ],
        string='نوع المستند', readonly=True,
    )
    payment_id = fields.Many2one('account.payment', string='الدفعة', readonly=True)
    payment_name = fields.Char(string='رقم الإشعار', readonly=True)
    payment_date = fields.Date(string='تاريخ السداد', readonly=True)
    payment_amount = fields.Monetary(string='قيمة السداد', readonly=True)
    payment_journal_type = fields.Selection(
        [
            ('cash', 'كاش'),
            ('bank', 'بنك'),
        ],
        string='نوع الدفعية', readonly=True,
    )
    payment_journal_name = fields.Char(string='الخزينة/البنك', readonly=True)
    currency_id = fields.Many2one('res.currency', string='العملة', readonly=True)
    company_id = fields.Many2one('res.company', string='الشركة', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    apr.id AS id,
                    am.id AS move_id,
                    am.invoice_date AS invoice_date,
                    am.partner_id AS partner_id,
                    am.invoice_origin AS invoice_origin,
                    am.amount_total AS amount_total,
                    am.amount_residual AS amount_residual,
                    am.payment_state AS payment_state,
                    am.move_type AS move_type,
                    am.currency_id AS currency_id,
                    am.company_id AS company_id,
                    ap.id AS payment_id,
                    pay_move.name AS payment_name,
                    ap.date AS payment_date,
                    apr.amount AS payment_amount,
                    aj.type AS payment_journal_type,
                    aj.name AS payment_journal_name
                FROM account_move am
                JOIN account_move_line aml_inv
                    ON aml_inv.move_id = am.id
                JOIN account_account acc
                    ON acc.id = aml_inv.account_id
                    AND acc.account_type IN ('asset_receivable', 'liability_payable')
                JOIN account_partial_reconcile apr
                    ON apr.debit_move_id = aml_inv.id OR apr.credit_move_id = aml_inv.id
                JOIN account_move_line aml_pay
                    ON (apr.debit_move_id = aml_pay.id AND apr.credit_move_id = aml_inv.id)
                    OR (apr.credit_move_id = aml_pay.id AND apr.debit_move_id = aml_inv.id)
                JOIN account_payment ap
                    ON ap.id = aml_pay.payment_id
                JOIN account_move pay_move
                    ON pay_move.id = ap.move_id
                JOIN account_journal aj
                    ON aj.id = ap.journal_id
                WHERE am.move_type IN ('out_invoice', 'out_refund')
                AND am.state = 'posted'
            )
        """ % self._table)
