# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class SalesPaymentsReportWizard(models.TransientModel):
    _name = 'sales.payments.report.wizard'
    _description = 'معالج تقرير المبيعات مع الدفعات المرتبطة'

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
    partner_id = fields.Many2one(
        'res.partner',
        string='العميل',
    )
    payment_journal_type = fields.Selection(
        [
            ('all', 'الكل'),
            ('cash', 'كاش فقط'),
            ('bank', 'بنك فقط'),
        ],
        string='نوع الدفعية',
        default='all',
        required=True,
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError('تاريخ البداية يجب أن يكون قبل تاريخ النهاية')

    def action_view_report(self):
        self.ensure_one()

        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ]

        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))

        if self.payment_journal_type != 'all':
            domain.append(('payment_journal_type', '=', self.payment_journal_type))

        return {
            'name': 'تقرير المبيعات مع الدفعات المرتبطة',
            'type': 'ir.actions.act_window',
            'res_model': 'sales.payments.report',
            'view_mode': 'list,pivot',
            'views': [
                (self.env.ref(
                    'sales_payments_report.view_sales_payments_report_tree'
                ).id, 'list'),
                (False, 'pivot'),
            ],
            'domain': domain,
            'search_view_id': [
                self.env.ref(
                    'sales_payments_report.view_sales_payments_report_search'
                ).id, 'search'],
            'target': 'current',
            'context': {
                'search_default_group_move': 1,
                'create': False,
                'edit': False,
                'delete': False,
            },
        }
