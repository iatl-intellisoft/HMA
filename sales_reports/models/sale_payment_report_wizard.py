# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SalePaymentReportWizard(models.TransientModel):
    _name = 'sale.payment.report.wizard'
    _description = 'Payment Details Report'

    date = fields.Date(string='Date')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Currency',
        readonly=True,
    )
    line_ids = fields.One2many(
        'sale.payment.report.line',
        'wizard_id',
        string='Lines',
        readonly=True,
    )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _classify_payment(self, payment, partial_amount, buckets):
        """Add partial_amount to the correct bucket based on journal type / method."""
        journal = payment.journal_id
        method_code = (payment.payment_method_code or '').lower()

        if journal.type == 'cash':
            buckets['cash'] += partial_amount
        elif journal.type == 'bank':
            if 'check' in method_code:
                buckets['cheque'] += partial_amount
            elif method_code == 'manual':
                buckets['transfer'] += partial_amount

    def _generate_lines(self):
        """(Re)generate report lines grouped by salesperson.

        We start from posted customer invoices, walk their reconciliation links
        to find payments, and filter those payments by payment.date (not
        invoice_date).  This correctly handles the common case where an invoice
        was issued on a previous date but paid today.

        NOTE: In Odoo 18 payments use state='in_process'/'paid' (not 'posted'),
        so we never filter account.payment by state — we reach payments only
        through the reconciliation API (matched_credit_ids → credit_move_id →
        payment_id) which returns any confirmed payment regardless of its state
        label.
        """
        self.line_ids.unlink()

        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
        ], order='invoice_user_id, name')

        # ── Aggregate by salesperson ──────────────────────────────────────────
        by_user = {}      # {user_id (int|False): {...}}
        user_map = {}     # {user_id: res.users record}

        for inv in invoices:
            user = inv.invoice_user_id
            uid = user.id or False

            # Per-invoice payment buckets (classified before rolling up to user)
            inv_buckets = {'cash': 0.0, 'cheque': 0.0, 'transfer': 0.0}

            for move_line in inv.line_ids.filtered(
                lambda l: l.account_id.account_type == 'asset_receivable'
            ):
                for partial in move_line.matched_credit_ids:
                    payment = partial.credit_move_id.payment_id
                    if not payment:
                        continue
                    # Date filter is on payment.date, NOT invoice_date
                    if self.date and payment.date != self.date:
                        continue
                    self._classify_payment(payment, partial.amount, inv_buckets)

            if uid not in by_user:
                by_user[uid] = {
                    'invoices_total': 0.0,
                    'cash': 0.0,
                    'cheque': 0.0,
                    'transfer': 0.0,
                }
                user_map[uid] = user

            by_user[uid]['invoices_total'] += inv.amount_total
            by_user[uid]['cash'] += inv_buckets['cash']
            by_user[uid]['cheque'] += inv_buckets['cheque']
            by_user[uid]['transfer'] += inv_buckets['transfer']

        # ── Create lines ──────────────────────────────────────────────────────
        seq = 1
        line_vals = []

        for uid, data in sorted(
            by_user.items(),
            key=lambda item: (user_map[item[0]].name or '') if item[0] else '',
        ):
            diff = data['invoices_total'] - (
                data['cash'] + data['cheque'] + data['transfer']
            )
            line_vals.append({
                'wizard_id': self.id,
                'sequence': seq,
                'user_id': uid,
                'invoices_total': data['invoices_total'],
                'cash_total': data['cash'],
                'cheque_total': data['cheque'],
                'transfer_total': data['transfer'],
                'difference': diff,
            })
            seq += 1

        self.env['sale.payment.report.line'].create(line_vals)

    # ── Public actions ────────────────────────────────────────────────────────

    def action_generate(self):
        self.ensure_one()
        self._generate_lines()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payment Details'),
            'res_model': 'sale.payment.report.line',
            'view_mode': 'list',
            'views': [(False, 'list')],
            'domain': [('wizard_id', '=', self.id)],
            'target': 'current',
            'context': dict(
                self.env.context,
                create=False,
                edit=False,
                delete=False,
            ),
        }

    def action_print_pdf(self):
        self.ensure_one()
        self._generate_lines()
        # Explicitly search for the freshly created lines to avoid a stale
        # One2many cache that would produce a blank PDF.
        lines = self.env['sale.payment.report.line'].search(
            [('wizard_id', '=', self.id)],
            order='sequence asc',
        )
        return (
            self.env.ref('sales_reports.action_sale_payment_report_pdf')
            .report_action(lines)
        )
