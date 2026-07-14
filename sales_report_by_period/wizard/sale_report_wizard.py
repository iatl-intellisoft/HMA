# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleReportWizard(models.TransientModel):
    _name = 'sale.report.wizard'
    _description = 'معالج تقرير مبيعات الأصناف بالفترة'

    date_from = fields.Date(
        string='من تاريخ', required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string='إلى تاريخ', required=True,
        default=fields.Date.context_today,
    )
    partner_id = fields.Many2one(
        'res.partner', string='عميل محدد (اختياري)',
        help='اتركه فارغاً لعرض كل العملاء',
    )
    salesperson_id = fields.Many2one(
        'res.users', string='المندوب (اختياري)',
        help='اتركه فارغاً لعرض كل المندوبين',
    )
    move_type_filter = fields.Selection([
        ('out_invoice', 'فواتير المبيعات فقط'),
        ('out_refund', 'مرتجعات المبيعات فقط'),
        ('both', 'الفواتير والمرتجعات معاً'),
    ], string='نوع الحركة', default='both', required=True)

    def _get_domain(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError('تاريخ البداية لازم يكون قبل أو يساوي تاريخ النهاية.')

        if self.move_type_filter == 'both':
            move_types = ['out_invoice', 'out_refund']
        else:
            move_types = [self.move_type_filter]

        domain = [
            ('move_type', 'in', move_types),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ]
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        if self.salesperson_id:
            domain.append(('invoice_user_id', '=', self.salesperson_id.id))
        return domain

    def action_print_report(self):
        self.ensure_one()
        moves = self.env['account.move'].search(self._get_domain(), order='invoice_date, name')
        if not moves:
            raise UserError('مفيش فواتير مطابقة للفترة والفلاتر المختارة.')
        report = self.env.ref('sales_report_by_period.action_report_sales_summary')
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        return report.report_action(moves.ids, data=data)

    def action_generate(self):
        """اسم بديل لنفس دالة الطباعة، للتوافق مع أي زرار بيستدعي action_generate"""
        return self.action_print_report()

    def action_view_report_screen(self):
        """يفتح نفس التقرير في المتصفح (HTML) قبل الطباعة"""
        self.ensure_one()
        moves = self.env['account.move'].search(self._get_domain(), order='invoice_date, name')
        if not moves:
            raise UserError('مفيش فواتير مطابقة للفترة والفلاتر المختارة.')
        report = self.env.ref('sales_report_by_period.action_report_sales_summary')
        action = report.report_action(moves.ids, data={
            'date_from': self.date_from,
            'date_to': self.date_to,
        })
        return action
