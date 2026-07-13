# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleReportWizard(models.TransientModel):
    _name = 'sale.report.wizard'
    _description = 'Sales Details Report'

    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')

    # ── Generation ────────────────────────────────────────────────────────────

    def action_generate(self):
        self.ensure_one()

        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(_("Start Date cannot be after End Date."))

        # Build invoice domain
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
        ]
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))

        invoices = self.env['account.move'].search(domain, order='invoice_date asc, name asc')

        # Remove any previously generated lines for this wizard session
        self.env['sale.report.line'].search([('wizard_id', '=', self.id)]).unlink()

        line_vals = []
        for inv in invoices:
            # ── Discount: sum of (unit_price × qty × discount%) on product lines only.
            #    In Odoo 18 display_type == 'product' for sellable lines (never False).
            total_discount = sum(
                line.price_unit * line.quantity * (line.discount / 100.0)
                for line in inv.invoice_line_ids
                if line.display_type == 'product' and line.discount
            )

            # ── Refunds: posted credit notes that reverse this invoice
            refund_total = sum(
                ref.amount_total
                for ref in inv.reversal_move_ids
                if ref.state == 'posted' and ref.move_type == 'out_refund'
            )

            # ── Net total: invoice amount after deducting refunds
            net_total = inv.amount_total - refund_total

            # ── Paid (cash only): total reconciled − credit-note reconciliation
            #    amount_residual is what remains after ALL reconciliation
            reconciled = inv.amount_total - inv.amount_residual
            paid = max(0.0, reconciled - refund_total)

            # ── Net outstanding: net_total − cash paid  (= amount_residual)
            net = max(0.0, net_total - paid)

            # ── Sale order ref: prefer the actual linked SO (works for all records),
            #    fall back to invoice_origin for manually-set references.
            sale_orders = inv.line_ids.sale_line_ids.order_id
            sale_order_ref = (
                ', '.join(sale_orders.mapped('name'))
                if sale_orders else (inv.invoice_origin or '')
            )
            payments = inv._get_reconciled_payments()

            bank_references = payments.filtered(
                lambda p: p.journal_id.type == 'bank' and p.bankak_transaction_number
            ).mapped('bankak_transaction_number')
            
            bank_reference = ', '.join(bank_references)
            
            line_vals.append({
                'wizard_id': self.id,
                'move_id': inv.id,
                'sale_order_ref': sale_order_ref,
                'invoice_date': inv.invoice_date,
                'salesperson_id': inv.invoice_user_id.id if inv.invoice_user_id else False,
                'partner_id': inv.partner_id.id,
                'currency_id': inv.currency_id.id,
                'total_discount': total_discount,
                'invoice_total': inv.amount_total,
                'refund_total': refund_total,
                'net_total': net_total,
                'paid': paid,
                'net': net,
                'bank_reference': bank_reference,
            })

        self.env['sale.report.line'].create(line_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Details'),
            'res_model': 'sale.report.line',
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
