from odoo import models, fields, api


class SalePaymentReportWizard(models.TransientModel):
    _name = 'sale.payment.report.wizard'
    _description = 'ويزارد تقرير سداد المبيعات'

    date_from = fields.Date(string='من تاريخ', required=True,
                             default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(string='إلى تاريخ', required=True,
                           default=lambda self: fields.Date.context_today(self))
    payment_method = fields.Selection([
        ('all', 'الكل'),
        ('bank', 'بنك'),
        ('cash', 'كاش'),
    ], string='طريقة السداد', default='all', required=True)

    line_ids = fields.One2many('sale.payment.report.line', 'wizard_id', string='الدفعيات', readonly=True)

    def _get_journal_type_label(self, journal):
        if journal.type == 'bank':
            return 'بنك'
        elif journal.type == 'cash':
            return 'كاش'
        return journal.name or ''

    def _fetch_lines(self):
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'posted'),
            ('payment_type', '=', 'inbound'),
        ]
        if self.payment_method != 'all':
            domain.append(('journal_id.type', '=', self.payment_method))

        payments = self.env['account.payment'].search(domain, order='date asc')

        vals_list = []
        for pay in payments:
            invoices = pay.reconciled_invoice_ids
            if not invoices:
                continue
            sale_orders = invoices.mapped('invoice_line_ids.sale_line_ids.order_id')
            if not sale_orders:
                continue
            # لتوزيع مبلغ الدفعة على كل أمر بيع مرتبط (في حال ارتبطت دفعة واحدة بأكثر من أمر بيع)
            amount_per_order = pay.amount / len(sale_orders)
            for so in sale_orders:
                vals_list.append((0, 0, {
                    'payment_id': pay.id,
                    'payment_name': pay.name,
                    'payment_date': pay.date,
                    'partner_id': pay.partner_id.id,
                    'sale_order_id': so.id,
                    'sale_order_name': so.name,
                    'payment_method_label': self._get_journal_type_label(pay.journal_id),
                    'amount': amount_per_order,
                }))
        return vals_list

    def action_preview(self):
        self.ensure_one()
        self.line_ids.unlink()
        self.write({'line_ids': self._fetch_lines()})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.payment.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def action_print_report(self):
        self.ensure_one()
        self.line_ids.unlink()
        self.write({'line_ids': self._fetch_lines()})
        return self.env.ref('sale_payment_report.action_report_sale_payment').report_action(self)


class SalePaymentReportLine(models.TransientModel):
    _name = 'sale.payment.report.line'
    _description = 'سطر تقرير سداد المبيعات'

    wizard_id = fields.Many2one('sale.payment.report.wizard', ondelete='cascade')
    payment_id = fields.Many2one('account.payment', string='الدفعة')
    payment_name = fields.Char(string='رقم الدفعة')
    payment_date = fields.Date(string='تاريخ الدفعة')
    partner_id = fields.Many2one('res.partner', string='العميل')
    sale_order_id = fields.Many2one('sale.order', string='أمر البيع')
    sale_order_name = fields.Char(string='رقم أمر البيع')
    payment_method_label = fields.Char(string='طريقة السداد')
    amount = fields.Monetary(string='قيمة السداد', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
