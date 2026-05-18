import time
from datetime import date, datetime
from num2words import num2words
from odoo import models, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class PayrollVoucherAbstract(models.AbstractModel):
    _name = 'report.hr_payroll_custom.voucher_report_template'

    @api.model
    def _get_report_values(self, docids, data=None):
        result = []
        result_lines = {}
        moves = self.env['account.move'].browse(docids)
        payslips = self.env['hr.payslip.run'].search([('voucher_ids', 'in', docids)])
        if payslips:
            domain = [('payslip_run_id', 'in', payslips.ids)]
            if moves[0].bank_id:
                domain.append(('bank_id', '=', moves[0].bank_id.id))
            else:
                domain.append(('bank_id', '=', False))
            payslips_ids = self.env['hr.payslip'].search(domain)
            payslips_ids = payslips_ids.filtered(
                lambda m: m.struct_id.partner_id and m.struct_id.partner_id == moves[0].partner_id)
        else:
            raise UserError(_('There is not payslip.'))
        if not payslips_ids:
            raise UserError(
                _('There is no payslip with structure include Salary partner same as the receipt partner. '))
        date, month = self._get_date(payslips[0].date_start)
        for pay in payslips_ids:
            result_lines = {}
            result_lines['employee'] = pay.employee_id.name
            result_lines['acc_number'] = pay.employee_id.bank_account_id.acc_number
            result_lines['amount'] = round(pay.net_wage, 2)
            result.append(result_lines)
        payslips_total = round(
            sum(payslip.line_ids.filtered(lambda m: m.category_id.code == 'NET').total for payslip in payslips_ids), 2)
        payslips_total_text = payslips[0].journal_id.currency_id.with_context(lang='ar_001').amount_to_text(
            payslips_total)
        return {
            'docs': self.env['account.move'].browse(docids),
            'result': result,
            'total': payslips_total,
            'total_text': payslips_total_text,
            'report_type': 'payroll',
            'date': date,
            'month': month}

    def _get_date(self, rec_date):
        date = month = False
        if rec_date:
            date = datetime.strptime(str(rec_date), '%Y-%m-%d')
            year = date.year
            if date.month == 1:
                month = 'يناير'
            if date.month == 2:
                month = 'فبراير'
            if date.month == 3:
                month = 'مارس'
            if date.month == 4:
                month = 'أبريل'
            if date.month == 5:
                month = 'مايو'
            if date.month == 6:
                month = 'يونيو'
            if date.month == 7:
                month = 'يوليو'
            if date.month == 8:
                month = 'أغسطس'
            if date.month == 9:
                month = 'سبتمبر'
            if date.month == 10:
                month = 'أكتوبر'
            if date.month == 11:
                month = 'نوفمبر'
            if date.month == 12:
                month = 'ديسمبر'
        return date, month
