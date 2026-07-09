# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_payment_state = fields.Selection([
        ('not_paid', 'غير مسددة'),
        ('in_payment', 'قيد السداد'),
        ('paid', 'مسددة بالكامل'),
        ('partial', 'مسددة جزئياً'),
        ('reversed', 'معكوسة'),
        ('invoicing_legacy', 'قديم'),
    ], string='حالة سداد الفاتورة', compute='_compute_sale_payment_state')

    @api.depends('sale_id.invoice_ids.payment_state')
    def _compute_sale_payment_state(self):
        for picking in self:
            invoices = picking.sale_id.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted'
            ) if picking.sale_id else False
            if invoices:
                states = invoices.mapped('payment_state')
                if any(s != 'paid' for s in states):
                    picking.sale_payment_state = next(s for s in states if s != 'paid')
                else:
                    picking.sale_payment_state = 'paid'
            else:
                picking.sale_payment_state = False

    def _get_related_sale_order(self):
        self.ensure_one()
        # sale_id متاح افتراضياً على stock.picking بفضل موديول sale_stock
        return self.sale_id

    def _check_full_payment_before_validation(self):

        for picking in self:
            if picking.picking_type_id.code != 'outgoing':
                continue

            sale = picking._get_related_sale_order()
            if not sale:
                continue

            if sale.partner_id.requires_sale_approval:
                continue

            invoices = sale.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted'
            )

            if not invoices:
                raise UserError(_(
                    'لا يمكن تأكيد التسليم "%s".\n'
                    'يجب أولاً إصدار فاتورة أمر البيع "%s" وسدادها بالكامل قبل تأكيد التوصيل.'
                ) % (picking.name, sale.name))

            unpaid_invoices = invoices.filtered(lambda inv: inv.payment_state != 'paid')
            if unpaid_invoices:
                state_labels = dict(
                    unpaid_invoices.fields_get(['payment_state'])['payment_state']['selection']
                )
                states_display = ', '.join(
                    state_labels.get(state, state)
                    for state in unpaid_invoices.mapped('payment_state')
                )
                raise UserError(_(
                    'لا يمكن تأكيد التسليم "%s".\n'
                    'فاتورة/فواتير أمر البيع "%s" غير مسددة بالكامل بعد (الحالة الحالية: %s).\n'
                    'يجب سداد كامل قيمة الفاتورة قبل تأكيد التوصيل لهذا العميل.'
                ) % (picking.name, sale.name, states_display))

    def button_validate(self):
        self._check_full_payment_before_validation()
        return super(StockPicking, self).button_validate()
