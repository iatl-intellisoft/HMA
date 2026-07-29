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
    # أصبح اختياريًا فقط لتضييق النتائج إن أراد المستخدم ذلك،
    # لم يعد هو المصدر الأساسي لتحديد الحسابات البنكية
    journal_ids = fields.Many2many(
        'account.journal',
        string='البنوك (اختياري - لتصفية إضافية)',
        domain=[('type', '=', 'bank')],
        help='اتركه خاليًا لعرض كل الحسابات البنكية بغض النظر عن الدفتر',
    )
    # الحقل الجديد: يسمح باختيار حسابات بنكية محددة مباشرة من شجرة الحسابات
    account_ids = fields.Many2many(
        'account.account',
        string='الحسابات البنكية (اختياري)',
        domain=[('account_type', '=', 'asset_cash')],
        help='اتركه خاليًا لعرض كل حسابات النوع "بنك/نقدية" في الشركة',
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

        return self.env.ref(
            'bank_trial_balance_report.action_report_bank_balance'
        ).report_action(self, data=data)

    # كلمات تدل على إن الحساب "خزينة/نقدية" مش "بنك"، تُستخدم فقط
    # للحسابات اللي مالها دفتر (journal) مربوط بيها بشكل مباشر
    _CASH_NAME_MARKERS = ['خزنة', 'خزينة', 'الخزينة', 'الخزنة']

    def _get_bank_accounts(self):
        """يرجع حسابات البنوك فقط (يستبعد الخزن/النقدية) المرتبطة
        بالشركة المختارة، بغض النظر عن وجود دفتر مربوط بيها أو لا."""
        self.ensure_one()
        Account = self.env['account.account']
        Journal = self.env['account.journal']

        if self.account_ids:
            accounts = self.account_ids
        else:
            accounts = Account.search([
                ('account_type', '=', 'asset_cash'),
                ('company_ids', 'in', self.company_id.id),
            ])

            # الحسابات المرتبطة بدفاتر نوعها "نقدية/خزينة" - نستبعدها
            cash_journal_accounts = Journal.search([
                ('type', '=', 'cash'),
                ('company_id', '=', self.company_id.id),
            ]).mapped('default_account_id')

            # الحسابات المرتبطة بدفاتر نوعها "بنك" - نضمّها أكيد
            bank_journal_accounts = Journal.search([
                ('type', '=', 'bank'),
                ('company_id', '=', self.company_id.id),
            ]).mapped('default_account_id')

            unlinked_accounts = accounts - cash_journal_accounts - bank_journal_accounts
            # من الحسابات غير المرتبطة بأي دفتر، نستبعد اللي اسمها
            # بيدل على إنها خزينة/نقدية (وليست بنك)
            cash_like_unlinked = unlinked_accounts.filtered(
                lambda a: any(marker in (a.name or '') for marker in self._CASH_NAME_MARKERS)
            )

            accounts = accounts - cash_journal_accounts - cash_like_unlinked

        # لو المستخدم حدد دفاتر بنكية بعينها، نستخدمها فقط لتضييق
        # قائمة الحسابات (وليس لتضييق الحركات المالية نفسها)
        if self.journal_ids:
            journal_accounts = self.journal_ids.mapped('default_account_id')
            accounts = accounts & journal_accounts if accounts else journal_accounts

        return accounts

    def _compute_lines(self):
        self.ensure_one()
        AML = self.env['account.move.line']
        accounts = self._get_bank_accounts()
        lines = []

        for account in accounts:
            # نفس منطق دفتر الأستاذ العام تمامًا: فلترة على الحساب
            # والشركة فقط، بدون قيد على الدفتر (journal_id)
            base_domain = [
                ('account_id', '=', account.id),
                ('parent_state', '=', 'posted'),
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
                'journal_name': account.name,
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
