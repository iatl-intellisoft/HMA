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
        help='اتركه خاليًا لعرض كل الحسابات البنكية (حتى لو مالهاش جورنال مربوط)',
    )
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        default=lambda self: self.env.company,
    )
    strict_journal_match = fields.Boolean(
        string='فلترة صارمة بالجورنال',
        default=False,
        help=(
            'اتركها بدون تفعيل عشان الأرقام تطابق دفتر الأستاذ '
            '(كل حركة على حساب البنك، من أي جورنال، هتتحسب).\n\n'
            'فعّلها فقط لو أكتر من بنك بيشتركوا في نفس الحساب المحاسبي '
            'وعايز كل بنك ياخد حركته هو بس (من جورنال البنك نفسه)، '
            'مع العلم إن ده هيستبعد القيود اليدوية أو التسويات '
            'المتسجلة من جورنال تاني على نفس الحساب. الحسابات اللي '
            'مالهاش جورنال مربوط مش هتتأثر بالخيار ده.'
        ),
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

    def _get_bank_accounts(self):
        """
        بيرجع list من (account, journal_or_False) بحيث كل حساب بنكي
        يظهر مرة واحدة بس، حتى لو ملوش جورنال مربوط، أو حتى لو أكتر
        من جورنال بيستخدموا نفس الحساب (السطر بيفضل واحد لكل حساب،
        والحركة كلها بتتجمع عليه إلا لو strict_journal_match مفعّلة).
        """
        self.ensure_one()
        Account = self.env['account.account']
        Journal = self.env['account.journal']

        if self.journal_ids:
            accounts = self.journal_ids.mapped('default_account_id')
            # لو فيه جورنالات من غيرهم مالهاش حساب، هنسيبهم يظهروا برسالة تنبيه
            result = []
            seen = set()
            for journal in self.journal_ids:
                account = journal.default_account_id
                if account and account.id in seen:
                    continue
                if account:
                    seen.add(account.id)
                result.append((account, journal))
            return result

        company_field = 'company_ids' if 'company_ids' in Account._fields else 'company_id'
        accounts = Account.search([
            ('account_type', '=', 'asset_cash'),
            (company_field, 'child_of', self.company_id.id),
        ])

        result = []
        for account in accounts:
            journal = Journal.search([
                ('default_account_id', '=', account.id),
                ('type', '=', 'bank'),
                ('company_id', 'child_of', self.company_id.id),
            ], limit=1)
            result.append((account, journal))
        return result

    def _compute_lines(self):
        """
        يحسب آخر رصيد لكل بنك (كل حساب بيظهر بسطر مستقل بيه) حتى
        تاريخ 'إلى تاريخ':
        آخر رصيد = الرصيد الافتتاحي (كل الحركة قبل 'من تاريخ')
                  + صافي الحركة (مدين - دائن) بين 'من تاريخ' و 'إلى تاريخ'

        - كل البنوك بتظهر حتى لو معهاش أي حركة خلال الفترة المحددة.

        - الفلترة الافتراضية بـ account_id بس (زي دفتر الأستاذ تمامًا)،
          عشان الأرقام تطابق المحاسبة. يعني أي قيد يدوي أو تسوية أو
          رصيد افتتاحي متسجل من جورنال تاني (زي "القيود اليومية"
          Miscellaneous) على نفس حساب البنك هيتحسب برضه.

        - فعّل 'strict_journal_match' بس لو عايز تفصل حركة كل بنك عن
          التاني في حالة اشتراك أكتر من بنك في نفس الحساب المحاسبي.
        """
        self.ensure_one()
        AML = self.env['account.move.line']
        accounts_and_journals = self._get_bank_accounts()
        lines = []

        for account, journal in accounts_and_journals:
            journal_name = journal.name if journal else False

            if not account:
                lines.append({
                    'journal_name': f"{journal_name or 'بنك بدون حساب'} (لا يوجد حساب مربوط)",
                    'account_code': '',
                    'account_name': '',
                    'initial_balance': 0.0,
                    'debit': 0.0,
                    'credit': 0.0,
                    'ending_balance': 0.0,
                })
                continue

            base_domain = [
                ('account_id', '=', account.id),
                ('parent_state', '=', 'posted'),
                ('company_id', 'child_of', self.company_id.id),
            ]

            if self.strict_journal_match and journal:
                base_domain.append(('journal_id', '=', journal.id))

            initial_lines = AML.search(base_domain + [('date', '<', self.date_from)])
            initial_balance = sum(initial_lines.mapped('debit')) - sum(initial_lines.mapped('credit'))

            period_lines = AML.search(
                base_domain + [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
            )
            debit = sum(period_lines.mapped('debit'))
            credit = sum(period_lines.mapped('credit'))

            ending_balance = initial_balance + debit - credit

            lines.append({
                'journal_name': journal_name or account.name,
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
