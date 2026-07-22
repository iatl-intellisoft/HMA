# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BankBalanceReportWizard(models.TransientModel):
    _name = 'bank.balance.report.wizard'
    _description = 'معالج تقرير أرصدة البنوك'

    date_from = fields.Date(
        string='من تاريخ',
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string='إلى تاريخ',
        required=True,
        default=fields.Date.context_today,
    )
    journal_ids = fields.Many2many(
        'account.journal',
        string='البنوك',
        domain=[('type', '=', 'bank')],
        help='اتركه خاليًا لعرض كل حسابات البنوك',
    )
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        default=lambda self: self.env.company,
    )

    def action_print_pdf(self):
        self.ensure_one()
        lines = self._compute_lines()
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_name': self.company_id.name,
            'lines': lines,
        }
        # نمرر البيانات المحسوبة جاهزة عبر data بدل الاعتماد على قراءة
        # الـ wizard تاني من docids، لأن آلية الطباعة بتاعة أودو ممكن
        # تستدعي get_report_values بأكتر من سجل أو بدون سجلات في حالة
        # التقارير اللي مصدرها TransientModel، وده كان بيسبب خطأ
        # "Expected singleton".
        return self.env.ref(
            'bank_trial_balance_report.action_report_bank_balance'
        ).report_action(self, data=data)

    def _get_journals(self):
        self.ensure_one()
        journals = self.journal_ids
        if not journals:
            journals = self.env['account.journal'].search([
                ('type', '=', 'bank'),
                ('company_id', '=', self.company_id.id),
            ])
        return journals

    def _compute_lines(self):
        """يحسب رصيد أول المدة، المدين، الدائن، ورصيد آخر المدة
        لكل حساب بنك، بالاعتماد على نفس بيانات دفتر الأستاذ العام
        (account.move.line) لكن مجمّعة بدون سطور تفصيلية."""
        self.ensure_one()
        AML = self.env['account.move.line']
        journals = self._get_journals()
        lines = []

        for journal in journals:
            account = journal.default_account_id
            if not account:
                continue

            base_domain = [
                ('account_id', '=', account.id),
                ('move_id.state', '=', 'posted'),
                ('company_id', '=', self.company_id.id),
            ]

            initial_lines = AML.search(base_domain + [('date', '<', self.date_from)])
            initial_balance = sum(initial_lines.mapped('debit')) - sum(initial_lines.mapped('credit'))

            period_lines = AML.search(
                base_domain + [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
            )
            debit = sum(period_lines.mapped('debit'))
            credit = sum(period_lines.mapped('credit'))
            ending_balance = initial_balance + debit - credit

            lines.append({
                'journal_name': journal.name,
                'account_code': account.code,
                'account_name': account.name,
                'initial_balance': initial_balance,
                'debit': debit,
                'credit': credit,
                'ending_balance': ending_balance,
            })

        return lines


class BankBalanceReportParser(models.AbstractModel):
    _name = 'report.bank_trial_balance_report.report_bank_balance_template'
    _description = 'تفسير بيانات تقرير أرصدة البنوك'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        lines = data.get('lines', [])

        total_initial = sum(l['initial_balance'] for l in lines)
        total_debit = sum(l['debit'] for l in lines)
        total_credit = sum(l['credit'] for l in lines)
        total_ending = sum(l['ending_balance'] for l in lines)

        return {
            'doc_ids': docids,
            'doc_model': 'bank.balance.report.wizard',
            'docs': [],
            'lines': lines,
            'date_from': data.get('date_from'),
            'date_to': data.get('date_to'),
            'company_name': data.get('company_name'),
            'total_initial': total_initial,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'total_ending': total_ending,
        }
