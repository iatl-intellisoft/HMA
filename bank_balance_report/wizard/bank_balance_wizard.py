# -*- coding: utf-8 -*-
import io
import base64
from datetime import date

from odoo import models, fields, api, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class BankBalanceWizard(models.TransientModel):
    _name = 'bank.balance.wizard'
    _description = 'Bank Balance Report Wizard'

    date_from = fields.Date(
        string='من تاريخ', required=True,
        default=lambda self: date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='إلى تاريخ', required=True,
        default=fields.Date.context_today
    )
    company_ids = fields.Many2many(
        'res.company', string='الشركات',
        default=lambda self: self.env.company
    )
    journal_ids = fields.Many2many(
        'account.journal', string='البنوك',
        domain="[('type', '=', 'bank'), ('company_id', 'in', company_ids)]",
        help='اتركه فارغاً لعرض جميع البنوك'
    )
    show_details = fields.Boolean(string='عرض التفاصيل')

    # ------------------------------------------------------------------
    # منطق الحساب
    # ------------------------------------------------------------------
    def _get_journals(self):
        """إرجاع Journals من نوع bank فقط، مع تطبيق الفلاتر المختارة"""
        domain = [('type', '=', 'bank')]
        companies = self.company_ids or self.env.company
        domain.append(('company_id', 'in', companies.ids))
        if self.journal_ids:
            domain.append(('id', 'in', self.journal_ids.ids))
        return self.env['account.journal'].search(domain, order='name')

    def _get_account_for_journal(self, journal):
        """الحساب البنكي المرتبط بالـ Journal"""
        return journal.default_account_id

    def _base_domain(self, account, companies):
        return [
            ('account_id', '=', account.id),
            ('parent_state', '=', 'posted'),
            ('company_id', 'in', companies.ids),
        ]

    def _compute_report_data(self):
        """
        يبني بنية بيانات التقرير:
        [{
            'journal': record,
            'account': record,
            'opening_balance': float,
            'debit': float,
            'credit': float,
            'closing_balance': float,
            'details': [ {date, move_name, label, debit, credit, balance}, ... ]
        }, ...]
        """
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_('تاريخ "من" يجب أن يكون قبل تاريخ "إلى".'))

        companies = self.company_ids or self.env.company
        AML = self.env['account.move.line']
        result = []
        grand_total = {'opening': 0.0, 'debit': 0.0, 'credit': 0.0, 'closing': 0.0}

        for journal in self._get_journals():
            account = self._get_account_for_journal(journal)
            if not account:
                # لا يوجد حساب مرتبط بهذا اليومية، تجاهله
                continue

            base_domain = self._base_domain(account, companies)

            # الرصيد الافتتاحي: كل الحركات قبل تاريخ البداية
            opening_lines = AML.search(base_domain + [('date', '<', self.date_from)])
            opening_balance = sum(opening_lines.mapped('debit')) - sum(opening_lines.mapped('credit'))

            # حركات الفترة
            period_domain = base_domain + [
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
            ]
            period_lines = AML.search(period_domain, order='date asc, id asc')
            debit_total = sum(period_lines.mapped('debit'))
            credit_total = sum(period_lines.mapped('credit'))
            closing_balance = opening_balance + debit_total - credit_total

            details = []
            if self.show_details:
                running_balance = opening_balance
                for line in period_lines:
                    running_balance += line.debit - line.credit
                    details.append({
                        'date': line.date,
                        'move_name': line.move_id.name or '/',
                        'label': line.name or line.move_id.ref or '',
                        'debit': line.debit,
                        'credit': line.credit,
                        'balance': running_balance,
                    })

            grand_total['opening'] += opening_balance
            grand_total['debit'] += debit_total
            grand_total['credit'] += credit_total
            grand_total['closing'] += closing_balance

            result.append({
                'journal': journal,
                'account': account,
                'opening_balance': opening_balance,
                'debit': debit_total,
                'credit': credit_total,
                'closing_balance': closing_balance,
                'details': details,
            })

        return result, grand_total

    # ------------------------------------------------------------------
    # الإجراءات
    # ------------------------------------------------------------------
    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref('bank_balance_report.action_report_bank_balance').report_action(self)

    def action_export_xlsx(self):
        self.ensure_one()
        if xlsxwriter is None:
            raise UserError(_(
                'مكتبة xlsxwriter غير مثبتة على السيرفر. الرجاء تثبيتها عبر:\n'
                'pip install xlsxwriter'
            ))

        data, grand_total = self._compute_report_data()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(_('Bank Balance'))
        sheet.right_to_left()

        # تنسيقات
        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'
        })
        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#D9E1F2', 'border': 1,
            'align': 'center', 'valign': 'vcenter'
        })
        cell_fmt = workbook.add_format({'border': 1, 'align': 'center'})
        money_fmt = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'align': 'center'})
        bold_money_fmt = workbook.add_format({
            'border': 1, 'num_format': '#,##0.00', 'bold': True,
            'bg_color': '#F2F2F2', 'align': 'center'
        })
        sub_header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#EDEDED', 'border': 1, 'align': 'center'
        })

        sheet.merge_range(0, 0, 0, 5, _('تقرير أرصدة الحسابات البنكية'), title_fmt)
        sheet.merge_range(
            1, 0, 1, 5,
            _('من %s إلى %s') % (self.date_from, self.date_to),
            workbook.add_format({'align': 'center', 'italic': True})
        )

        row = 3
        headers = [_('البنك'), _('الرصيد الافتتاحي'), _('المقبوضات'), _('المدفوعات'), _('الرصيد الختامي')]
        for col, h in enumerate(headers):
            sheet.write(row, col, h, header_fmt)
        row += 1

        detail_headers = [_('التاريخ'), _('رقم القيد'), _('البيان'), _('مدين'), _('دائن'), _('الرصيد')]

        for line in data:
            journal = line['journal']
            sheet.write(row, 0, journal.name, cell_fmt)
            sheet.write(row, 1, line['opening_balance'], money_fmt)
            sheet.write(row, 2, line['debit'], money_fmt)
            sheet.write(row, 3, line['credit'], money_fmt)
            sheet.write(row, 4, line['closing_balance'], money_fmt)
            row += 1

            if self.show_details and line['details']:
                for col, h in enumerate(detail_headers):
                    sheet.write(row, col, h, sub_header_fmt)
                row += 1
                for d in line['details']:
                    sheet.write(row, 0, str(d['date']), cell_fmt)
                    sheet.write(row, 1, d['move_name'], cell_fmt)
                    sheet.write(row, 2, d['label'], cell_fmt)
                    sheet.write(row, 3, d['debit'], money_fmt)
                    sheet.write(row, 4, d['credit'], money_fmt)
                    sheet.write(row, 5, d['balance'], money_fmt)
                    row += 1
                row += 1  # سطر فارغ بعد تفاصيل كل بنك

        # الإجمالي العام
        sheet.write(row, 0, _('الإجمالي'), sub_header_fmt)
        sheet.write(row, 1, grand_total['opening'], bold_money_fmt)
        sheet.write(row, 2, grand_total['debit'], bold_money_fmt)
        sheet.write(row, 3, grand_total['credit'], bold_money_fmt)
        sheet.write(row, 4, grand_total['closing'], bold_money_fmt)

        sheet.set_column(0, 0, 22)
        sheet.set_column(1, 5, 18)

        workbook.close()
        output.seek(0)
        file_data = output.read()

        attachment = self.env['ir.attachment'].create({
            'name': 'Bank_Balance_Report_%s_%s.xlsx' % (self.date_from, self.date_to),
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'res_model': 'bank.balance.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }
