# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class InvoiceReportWizard(models.TransientModel):
    _name = 'invoice.report.wizard'
    _description = 'معالج تقرير الفواتير بالمنتجات'

    date_from = fields.Date(
        string='من تاريخ',
        required=True,
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string='إلى تاريخ',
        required=True,
        default=fields.Date.context_today,
    )
    move_type = fields.Selection(
        [
            ('out_invoice', 'فواتير المبيعات'),
            ('in_invoice', 'فواتير المشتريات'),
            ('all', 'الكل'),
        ],
        string='نوع الفاتورة',
        default='out_invoice',
        required=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='العميل / المورد',
    )
    product_id = fields.Many2one(
        'product.product',
        string='المنتج',
    )
    only_posted = fields.Boolean(
        string='الفواتير المرحلة فقط',
        default=True,
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError('تاريخ البداية يجب أن يكون قبل تاريخ النهاية')

    def action_view_report(self):
        self.ensure_one()

        domain = [
            ('display_type', '=', 'product'),
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
        ]

        if self.move_type != 'all':
            domain.append(('move_id.move_type', '=', self.move_type))
        else:
            domain.append(('move_id.move_type', 'in',
                            ['out_invoice', 'in_invoice']))

        if self.only_posted:
            domain.append(('parent_state', '=', 'posted'))

        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))

        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))

        return {
            'name': 'تقرير الفواتير بالمنتجات',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,pivot',
            'views': [
                (self.env.ref(
                    'invoice_products_report.view_invoice_report_line_tree'
                ).id, 'list'),
                (False, 'pivot'),
            ],
            'domain': domain,
            'search_view_id': [
                self.env.ref(
                    'invoice_products_report.view_invoice_report_search'
                ).id, 'search'],
            'target': 'current',
            'context': {
                'search_default_group_product': 1,
                'create': False,
                'edit': False,
                'delete': False,
            },
        }

    def action_view_payment_report(self):
        """يعرض فواتير المبيعات في الفترة المحددة مع كل الدفعات
        المرتبطة بكل فاتورة (نوع الدفعية، قيمة السداد، رقم الإشعار)،
        بالإضافة إلى رقم أمر البيع المصدر لكل فاتورة."""
        self.ensure_one()

        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
        ]

        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))

        return {
            'name': 'تقرير المبيعات مع الدفعات المرتبطة',
            'type': 'ir.actions.act_window',
            'res_model': 'account.invoice.payment.report',
            'view_mode': 'list,pivot',
            'views': [
                (self.env.ref(
                    'invoice_products_report.view_invoice_payment_report_tree'
                ).id, 'list'),
                (False, 'pivot'),
            ],
            'domain': domain,
            'search_view_id': [
                self.env.ref(
                    'invoice_products_report.view_invoice_payment_report_search'
                ).id, 'search'],
            'target': 'current',
            'context': {
                'search_default_group_move': 1,
                'create': False,
                'edit': False,
                'delete': False,
            },
        }
