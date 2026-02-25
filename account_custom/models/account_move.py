from odoo import api, fields, models, _, tools
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from collections import defaultdict
from odoo.tools import (
    create_index,
    date_utils,
    float_compare,
    float_is_zero,
    float_repr,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    groupby,
    index_exists,
    OrderedSet,
    SQL,
)


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange('type')
    def fill_partner(self):
        if self.move_type in ['in_invoice', 'in_receipt', 'in_refund']:
            return {'domain': {
                'partner_id': [('vendor', '=', True)]}}

        else:
            return {'domain': {
                'partner_id': [('customer', '=', True)]}}

    # @api.depends('amount_residual', 'move_type', 'state', 'company_id', 'matched_payment_ids.state')
    # def _compute_payment_state(self):
    #     stored_ids = tuple(self.ids)
    #     if stored_ids:
    #         self.env['account.partial.reconcile'].flush_model()
    #         self.env['account.payment'].flush_model(['is_matched'])
    #
    #         queries = []
    #         for source_field, counterpart_field in (
    #                 ('debit_move_id', 'credit_move_id'),
    #                 ('credit_move_id', 'debit_move_id'),
    #         ):
    #             queries.append(SQL('''
    #                     SELECT
    #                         source_line.id AS source_line_id,
    #                         source_line.move_id AS source_move_id,
    #                         account.account_type AS source_line_account_type,
    #                         ARRAY_AGG(counterpart_move.move_type) AS counterpart_move_types,
    #                         COALESCE(BOOL_AND(COALESCE(pay.is_matched, FALSE))
    #                             FILTER (WHERE counterpart_move.origin_payment_id IS NOT NULL), TRUE) AS all_payments_matched,
    #                         BOOL_OR(COALESCE(BOOL(pay.id), FALSE)) as has_payment,
    #                         BOOL_OR(COALESCE(BOOL(counterpart_move.statement_line_id), FALSE)) as has_st_line
    #                     FROM account_partial_reconcile part
    #                     JOIN account_move_line source_line ON source_line.id = part.%s
    #                     JOIN account_account account ON account.id = source_line.account_id
    #                     JOIN account_move_line counterpart_line ON counterpart_line.id = part.%s
    #                     JOIN account_move counterpart_move ON counterpart_move.id = counterpart_line.move_id
    #                     LEFT JOIN account_payment pay ON pay.id = counterpart_move.origin_payment_id
    #                     WHERE source_line.move_id IN %s AND counterpart_line.move_id != source_line.move_id
    #                     GROUP BY source_line.id, source_line.move_id, account.account_type
    #             ''', SQL.identifier(source_field), SQL.identifier(counterpart_field), stored_ids))
    #
    #         payment_data = defaultdict(list)
    #         for row in self.env.execute_query_dict(SQL(" UNION ALL ").join(queries)):
    #             payment_data[row['source_move_id']].append(row)
    #     else:
    #         payment_data = {}
    #
    #     for invoice in self:
    #         if invoice.payment_state == 'invoicing_legacy':
    #             # invoicing_legacy state is set via SQL when setting setting field
    #             # invoicing_switch_threshold (defined in account_accountant).
    #             # The only way of going out of this state is through this setting,
    #             # so we don't recompute it here.
    #             continue
    #
    #         currencies = set()
    #
    #         for line in invoice.line_ids:
    #             if line.currency_id and line in invoice._get_lines_onchange_currency():
    #                 currencies.add(line.currency_id)
    #
    #         # currencies = invoice._get_lines_onchange_currency().currency_id
    #         currency = len(currencies) == 1 and currencies.pop() or invoice.company_id.currency_id
    #         # currency = currencies if len(currencies) == 1 else invoice.company_id.currency_id
    #         reconciliation_vals = payment_data.get(invoice.id, [])
    #         payment_state_matters = invoice.is_invoice(True)
    #
    #         # Restrict on 'receivable'/'payable' lines for invoices/expense entries.
    #         if payment_state_matters:
    #             reconciliation_vals = [x for x in reconciliation_vals if
    #                                    x['source_line_account_type'] in ('asset_receivable', 'liability_payable')]
    #
    #         new_pmt_state = 'not_paid' if invoice.payment_state != 'blocked' else 'blocked'
    #         if invoice.state == 'posted':
    #
    #             # Posted invoice/expense entry.
    #             if payment_state_matters:
    #
    #                 if currency.is_zero(invoice.amount_residual):
    #                     if any(x['has_payment'] or x['has_st_line'] for x in reconciliation_vals):
    #
    #                         # Check if the invoice/expense entry is fully paid or 'in_payment'.
    #                         if all(x['all_payments_matched'] for x in reconciliation_vals):
    #                             new_pmt_state = 'paid'
    #                         else:
    #                             new_pmt_state = invoice._get_invoice_in_payment_state()
    #
    #                     else:
    #                         new_pmt_state = 'paid'
    #
    #                         reverse_move_types = set()
    #                         for x in reconciliation_vals:
    #                             for move_type in x['counterpart_move_types']:
    #                                 reverse_move_types.add(move_type)
    #
    #                         in_reverse = (invoice.move_type in ('in_invoice', 'in_receipt')
    #                                       and (reverse_move_types == {'in_refund'} or reverse_move_types == {
    #                                     'in_refund', 'entry'}))
    #                         out_reverse = (invoice.move_type in ('out_invoice', 'out_receipt')
    #                                        and (reverse_move_types == {'out_refund'} or reverse_move_types == {
    #                                     'out_refund', 'entry'}))
    #                         misc_reverse = (invoice.move_type in ('entry', 'out_refund', 'in_refund')
    #                                         and reverse_move_types == {'entry'})
    #                         if in_reverse or out_reverse or misc_reverse:
    #                             new_pmt_state = 'reversed'
    #                 elif invoice.matched_payment_ids.filtered(lambda p: not p.move_id and p.state == 'in_process'):
    #                     new_pmt_state = invoice._get_invoice_in_payment_state()
    #                 elif reconciliation_vals:
    #                     new_pmt_state = 'partial'
    #                 elif invoice.matched_payment_ids.filtered(lambda p: not p.move_id and p.state == 'paid'):
    #                     new_pmt_state = invoice._get_invoice_in_payment_state()
    #         invoice.payment_state = new_pmt_state


    def _recompute_payment_terms_lines(self):
        ''' Overwrite to solve allowed payable/receivable in invoice lines'''
        self.ensure_one()
        self = self.with_company(self.company_id)
        in_draft_mode = self != self._origin
        today = fields.Date.context_today(self)
        self = self.with_company(self.journal_id.company_id)

        def _get_payment_terms_computation_date(self):
            ''' Get the date from invoice that will be used to compute the payment terms.
            :param self:    The current account.move record.
            :return:        A datetime.date object.
            '''
            if self.invoice_payment_term_id:
                return self.invoice_date or today
            else:
                return self.invoice_date_due or self.invoice_date or today

        def _get_payment_terms_account(self, payment_terms_lines):
            ''' Get the account from invoice that will be set as receivable / payable account.
            :param self:                    The current account.move record.
            :param payment_terms_lines:     The current payment terms lines.
            :return:                        An account.account record.
            '''
            if payment_terms_lines:
                # Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
                return payment_terms_lines[0].account_id
            elif self.partner_id:
                # Retrieve account from partner.
                if self.is_sale_document(include_receipts=True):
                    return self.partner_id.property_account_receivable_id
                else:
                    return self.partner_id.property_account_payable_id
            else:
                # Search new account.
                domain = [
                    ('company_id', '=', self.company_id.id),
                    ('internal_type', '=', 'receivable' if self.move_type in (
                        'out_invoice', 'out_refund', 'out_receipt') else 'payable'),
                ]
                return self.env['account.account'].search(domain, limit=1)

        def _compute_payment_terms(self, date, total_balance, total_amount_currency):
            ''' Compute the payment terms.
            :param self:                    The current account.move record.
            :param date:                    The date computed by '_get_payment_terms_computation_date'.
            :param total_balance:           The invoice's total in company's currency.
            :param total_amount_currency:   The invoice's total in invoice's currency.
            :return:                        A list <to_pay_company_currency, to_pay_invoice_currency, due_date>.
            '''
            if self.invoice_payment_term_id:
                to_compute = self.invoice_payment_term_id.compute(total_balance, date_ref=date,
                                                                  currency=self.company_id.currency_id)
                if self.currency_id == self.company_id.currency_id:
                    # Single-currency.
                    return [(b[0], b[1], b[1]) for b in to_compute]
                else:
                    # Multi-currencies.
                    to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency, date_ref=date,
                                                                               currency=self.currency_id)
                    return [(b[0], b[1], ac[1]) for b, ac in zip(to_compute, to_compute_currency)]
            else:
                return [(fields.Date.to_string(date), total_balance, total_amount_currency)]

        def _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute):
            ''' Process the result of the '_compute_payment_terms' method and creates/updates corresponding invoice lines.
            :param self:                    The current account.move record.
            :param existing_terms_lines:    The current payment terms lines.
            :param account:                 The account.account record returned by '_get_payment_terms_account'.
            :param to_compute:              The list returned by '_compute_payment_terms'.
            '''
            # As we try to update existing lines, sort them by due date.
            existing_terms_lines = existing_terms_lines.sorted(
                lambda line: line.date_maturity or today)
            existing_terms_lines_index = 0

            # Recompute amls: update existing line or create new one for each payment term.
            new_terms_lines = self.env['account.move.line']
            for date_maturity, balance, amount_currency in to_compute:
                if self.journal_id.company_id.currency_id.is_zero(balance) and len(to_compute) > 1:
                    continue

                if existing_terms_lines_index < len(existing_terms_lines):
                    # Update existing line.
                    candidate = existing_terms_lines[existing_terms_lines_index]
                    existing_terms_lines_index += 1
                    candidate.update({
                        'date_maturity': date_maturity,
                        'amount_currency': -amount_currency,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                    })
                else:
                    # Create new line.
                    create_method = in_draft_mode and self.env['account.move.line'].new or self.env[
                        'account.move.line'].create
                    candidate = create_method({
                        'name': self.payment_reference or self.ref or '',
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'quantity': 1.0,
                        'amount_currency': -amount_currency,
                        'date_maturity': date_maturity,
                        'move_id': self.id,
                        'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                        'account_id': account.id,
                        'partner_id': self.commercial_partner_id.id,
                        'exclude_from_invoice_tab': True,
                    })
                new_terms_lines += candidate
                if in_draft_mode:
                    candidate.update(candidate._get_fields_onchange_balance(force_computation=True))
            return new_terms_lines

        # existing_terms_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        # others_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
        existing_terms_lines = self.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable',
                                                                                                    'liability_payable') and line.exclude_from_invoice_tab == True)
        others_lines = self.line_ids.filtered(lambda line: not (line.account_id.account_type in ('asset_receivable',
                                                                                                 'liability_payable') and line.exclude_from_invoice_tab == True))
        company_currency_id = (self.company_id or self.env.company).currency_id
        total_balance = sum(others_lines.mapped(lambda l: company_currency_id.round(l.balance)))
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        if not others_lines:
            self.line_ids -= existing_terms_lines
            return

        computation_date = _get_payment_terms_computation_date(self)
        account = _get_payment_terms_account(self, existing_terms_lines)
        to_compute = _compute_payment_terms(self, computation_date, total_balance, total_amount_currency)
        new_terms_lines = _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute)

        # Remove old terms lines that are no longer needed.
        self.line_ids -= existing_terms_lines - new_terms_lines

        if new_terms_lines:
            self.payment_reference = new_terms_lines[-1].name or ''
            self.invoice_date_due = new_terms_lines[-1].date_maturity

    def _compute_payments_widget_to_reconcile_info(self):
        for move in self:
            move.invoice_outstanding_credits_debits_widget = False
            move.invoice_has_outstanding = False

            if move.state != 'posted' \
                    or move.payment_state not in ('not_paid', 'partial') \
                    or not move.is_invoice(include_receipts=True):
                continue

            pay_term_lines = move.line_ids \
                .filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))

            domain = [
                ('account_id', 'in', pay_term_lines.account_id.ids),
                ('move_id.state', '=', 'posted'),
                ('partner_id', '=', move.commercial_partner_id.id),
                ('reconciled', '=', False),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
                '&',
                '|',
                ('display_type', 'in', ('product', 'rounding')),
                '&',
                ('display_type', 'not in', ('product', 'rounding')),
                ('move_id.move_type', '=', 'entry'),
            ]
            payments_widget_vals = {'outstanding': True, 'content': [], 'move_id': move.id}

            if move.is_inbound():
                domain.append(('balance', '<', 0.0))
                payments_widget_vals['title'] = _('Outstanding credits')
            else:
                domain.append(('balance', '>', 0.0))
                payments_widget_vals['title'] = _('Outstanding debits')

            for line in self.env['account.move.line'].search(domain):
                if line.currency_id == move.currency_id:
                    # Same foreign currency.
                    amount = abs(line.amount_residual_currency)
                else:
                    # Different foreign currencies.
                    amount = move.company_currency_id._convert(
                        abs(line.amount_residual),
                        move.currency_id,
                        move.company_id,
                        line.date,
                    )

                if move.currency_id.is_zero(amount):
                    continue

                payments_widget_vals['content'].append({
                    'journal_name': line.ref or line.move_id.name,
                    'amount': amount,
                    'currency_id': move.currency_id.id,
                    'id': line.id,
                    'move_id': line.move_id.id,
                    'date': fields.Date.to_string(line.date),
                    'account_payment_id': line.payment_id.id,
                })
            if not payments_widget_vals['content']:
                continue

            move.invoice_outstanding_credits_debits_widget = payments_widget_vals
            move.invoice_has_outstanding = True


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange('account_id')
    def _onchange_account_id(self):
        '''Overwrite to solve allowed payable/receivable in invoice lines
        '''
        if not self.display_type and (self.account_id.tax_ids or not self.tax_ids):
            taxes = self._get_computed_taxes()

            if taxes and self.move_id.fiscal_position_id:
                taxes = self.move_id.fiscal_position_id.map_tax(
                    taxes, partner=self.partner_id)

            self.tax_ids = taxes
        if self.account_id.account_type in ('asset_receivable', 'liability_payable'):
            self.partner_id = self.move_id.partner_id

    def reconcile(self):
        """
        """
        if not self:
            return
        lines = self.filtered(
            lambda line: not (line.display_type not in ('product', 'rounding') and line.move_id.move_type != 'entry'))
        return super(AccountMoveLine, self).reconcile()
