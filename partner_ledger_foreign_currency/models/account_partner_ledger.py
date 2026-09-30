# -*- coding: utf-8 -*-
"""
Partner Ledger – Foreign Currency Display
=========================================
Extends the standard Partner Ledger report handler to support a
"Display Foreign Currencies" mode.

When the option is active the report:
  • Groups each partner's journal items by the transaction currency
    (account_move_line.currency_id).
  • Shows Debit / Credit / Balance using amount_currency instead of the
    company-currency converted amounts.
  • Each (partner, currency) pair appears as its own summary row.
  • Expanding a row shows the individual journal items for that pair,
    with running balance in the transaction currency.
  • An Initial Balance line is shown when the date filter is a range.
"""

from collections import defaultdict
from copy import deepcopy
from datetime import timedelta

from odoo import _, fields, models
from odoo.osv import expression
from odoo.tools import SQL


class PartnerLedgerForeignCurrencyHandler(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    # ─────────────────────────────────────────────────────────────────────────
    # OPTIONS
    # ─────────────────────────────────────────────────────────────────────────

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['display_foreign_currency'] = (previous_options or {}).get('display_foreign_currency', False)
        self._drop_unrelated_no_partner_catch_all(options)

    def _drop_unrelated_no_partner_catch_all(self, options):
        """
        The base Partner Ledger handler (account_reports) widens the print
        domain with an unconditional ('partner_id', '=', False) clause
        whenever printing while a partner search-bar filter is active:

            OR(matched via debit reconciliation,
               OR(matched via credit reconciliation,
                  OR(partner name matches search, ANY line with no partner)))

        That last branch drags *every* no-partner journal item in the
        company (e.g. manual entries posted straight to a
        receivable/payable account) into a single-partner printout, even
        when they have no relation to the printed partner at all.

        We keep the two legitimate cases — entries reconciled with the
        searched partner, or whose own partner name matches — and drop
        only the unconditional catch-all, restoring balanced polish
        notation:
            ['|', A, '|', B, '|', C, D]  ->  ['|', A, '|', B, C]

        If the base domain shape ever changes, the pattern simply won't
        match and this is a no-op (fails open, never raises).
        """
        if options.get('export_mode') != 'print' or not options.get('filter_search_bar'):
            return
        domain = options.get('forced_domain')
        if not domain:
            return
        catch_all = ('partner_id', '=', False)
        if len(domain) >= 7 and domain[-1] == catch_all and domain[-3] == '|':
            del domain[-1]  # drop the catch-all tuple
            del domain[-2]  # drop the now-redundant '|' operator before it

    # ─────────────────────────────────────────────────────────────────────────
    # TOP-LEVEL LINES GENERATOR
    # ─────────────────────────────────────────────────────────────────────────

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        if not options.get('display_foreign_currency'):
            return super()._dynamic_lines_generator(
                report, options, all_column_groups_expression_totals, warnings=warnings
            )

        partner_lines, _totals = self._build_partner_lines(report, options)

        # Reuse the standard prefix-grouping mechanism but wire a
        # currency-aware expand function so unfolding a prefix group still
        # uses the foreign-currency query.
        lines = report._regroup_lines_by_name_prefix(
            options,
            partner_lines,
            '_report_expand_unfoldable_line_partner_ledger_currency_prefix_group',
            0,
        )
        # No grand-total line in foreign currency mode (amounts are in mixed
        # currencies and cannot be meaningfully summed).
        return [(0, line) for line in lines]

    # ─────────────────────────────────────────────────────────────────────────
    # PARTNER SUMMARY LINES
    # ─────────────────────────────────────────────────────────────────────────

    def _build_partner_lines(self, report, options, level_shift=0):
        if not options.get('display_foreign_currency'):
            return super()._build_partner_lines(report, options, level_shift=level_shift)
        return self._build_partner_currency_lines(report, options, level_shift=level_shift)

    def _build_partner_currency_lines(self, report, options, level_shift=0):
        lines = []
        totals_by_column_group = {
            cg_key: {'debit': 0.0, 'credit': 0.0, 'balance': 0.0, 'amount': 0.0}
            for cg_key in options['column_groups']
        }
        for (partner, currency), results in self._query_partners_by_currency(report, options):
            partner_values = defaultdict(dict)
            for cg_key in options['column_groups']:
                partner_sum = results.get(cg_key, {})
                for field in ('debit', 'credit', 'balance', 'amount'):
                    partner_values[cg_key][field] = partner_sum.get(field, 0.0)

            lines.append(
                self._get_report_line_partner_currency(
                    options, partner, currency, partner_values, level_shift=level_shift
                )
            )
        return lines, totals_by_column_group

    def _query_partners_by_currency(self, report, options):
        """
        Execute the summary query and return a list of
        ((partner_record, currency_record), column_group_values) tuples,
        sorted by partner name then currency name.
        """
        groupby = {}
        self._cr.execute(self._get_query_sums_by_currency(report, options))
        for res in self._cr.dictfetchall():
            key = (res['partner_id'], res['currency_id'])
            groupby.setdefault(key, defaultdict(lambda: defaultdict(float)))
            for f in ('debit', 'credit', 'balance', 'amount'):
                groupby[key][res['column_group_key']][f] += res[f]

        partner_ids = [k[0] for k in groupby if k[0] is not None]
        currency_ids = list({k[1] for k in groupby if k[1] is not None})

        partners_map = {
            p.id: p
            for p in self.env['res.partner'].with_context(active_test=False).browse(partner_ids)
        }
        currencies_map = {
            c.id: c
            for c in self.env['res.currency'].browse(currency_ids)
        }

        results = [
            (
                (partners_map.get(pid), currencies_map.get(cid)),
                vals,
            )
            for (pid, cid), vals in groupby.items()
        ]
        results.sort(key=lambda x: (
            x[0][0].name if x[0][0] else '￿',
            x[0][1].name if x[0][1] else '',
        ))
        return results

    def _get_query_sums_by_currency(self, report, options) -> SQL:
        """
        Build the summary SQL.
        Amounts come from amount_currency (the original transaction currency),
        grouped by (partner_id, currency_id).
        """
        queries = []
        for cg_key, cg_options in report._split_options_per_column_group(options).items():
            query = report._get_report_query(cg_options, 'from_beginning')
            date_from = options['date']['date_from']
            queries.append(SQL(
                """
                (WITH partner_sums AS (
                    SELECT
                        account_move_line.partner_id                                        AS partner_id,
                        account_move_line.currency_id                                       AS currency_id,
                        %(column_group_key)s                                                AS column_group_key,
                        SUM(CASE WHEN account_move_line.amount_currency > 0
                                 THEN  account_move_line.amount_currency
                                 ELSE  0 END)                                               AS debit,
                        SUM(CASE WHEN account_move_line.amount_currency < 0
                                 THEN -account_move_line.amount_currency
                                 ELSE  0 END)                                               AS credit,
                        SUM(account_move_line.amount_currency)                              AS balance,
                        SUM(account_move_line.amount_currency)                              AS amount,
                        BOOL_AND(account_move_line.reconciled)                              AS all_reconciled,
                        MAX(account_move_line.date)                                         AS latest_date
                    FROM %(table_references)s
                    WHERE %(search_condition)s
                    GROUP BY account_move_line.partner_id, account_move_line.currency_id
                )
                SELECT *
                FROM partner_sums
                WHERE  partner_sums.balance     != 0
                   OR  partner_sums.all_reconciled = FALSE
                   OR  partner_sums.latest_date >= %(date_from)s
                )""",
                column_group_key=cg_key,
                table_references=query.from_clause,
                search_condition=query.where_clause,
                date_from=date_from,
            ))
        return SQL(' UNION ALL ').join(queries)

    def _get_report_line_partner_currency(self, options, partner, currency, partner_values, level_shift=0):
        """Build the summary dict for one (partner, currency) row."""
        company_currency = self.env.company.currency_id
        col_currency = currency or company_currency
        report = self.env['account.report'].browse(options['report_id'])

        column_values = []
        for column in options['columns']:
            col_expr = column['expression_label']
            raw_value = (
                None if options.get('hide_partner_totals')
                else partner_values[column['column_group_key']].get(col_expr)
            )
            if col_expr in ('debit', 'credit', 'balance', 'amount') and raw_value is not None:
                column_values.append(
                    report._build_column_dict(raw_value, column, options=options, currency=col_currency)
                )
            else:
                # String / date columns and amount_currency: leave blank at summary level
                column_values.append(report._build_column_dict(None, column, options=options))

        # Encode currency into the markup so the expand function can recover it.
        currency_id = currency.id if currency else 0
        markup = f'fc_{currency_id}'
        if partner:
            line_id = report._get_generic_line_id('res.partner', partner.id, markup=markup)
        else:
            line_id = report._get_generic_line_id('res.partner', None, markup=f'no_partner_{markup}')

        unfoldable = any(
            not col_currency.is_zero(partner_values[cg_key].get(f, 0.0))
            for cg_key in options['column_groups']
            for f in ('debit', 'credit')
        )

        # Show currency code in brackets after the partner name so the user
        # can tell apart rows for the same partner in different currencies.
        name = (partner.name[:128] if partner else self._get_no_partner_line_label())
        if currency:
            name = f'{name} [{currency.name}]'

        return {
            'id': line_id,
            'name': name,
            'columns': column_values,
            'level': 1 + level_shift,
            'trust': partner.trust if partner else None,
            'unfoldable': unfoldable,
            'unfolded': line_id in options['unfolded_lines'] or options['unfold_all'],
            'expand_function': '_report_expand_unfoldable_line_partner_ledger_currency',
        }

    # ─────────────────────────────────────────────────────────────────────────
    # PREFIX-GROUP EXPAND (foreign currency mode)
    # ─────────────────────────────────────────────────────────────────────────

    def _report_expand_unfoldable_line_partner_ledger_currency_prefix_group(
        self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None
    ):
        """Expand a prefix group (e.g. "AZU…") in foreign currency mode."""
        report = self.env['account.report'].browse(options['report_id'])
        matched_prefix = report._get_prefix_groups_matched_prefix_from_line_id(line_dict_id)

        prefix_domain = [('partner_id.name', '=ilike', f'{matched_prefix}%')]
        if self._get_no_partner_line_label().upper().startswith(matched_prefix):
            prefix_domain = expression.OR([prefix_domain, [('partner_id', '=', None)]])

        expand_options = {
            **options,
            'forced_domain': options.get('forced_domain', []) + prefix_domain,
        }
        parent_level = len(matched_prefix) * 2
        partner_lines, _dummy = self._build_partner_currency_lines(
            report, expand_options, level_shift=parent_level
        )

        for pl in partner_lines:
            pl['id'] = report._build_subline_id(line_dict_id, pl['id'])
            pl['parent_id'] = line_dict_id

        lines = report._regroup_lines_by_name_prefix(
            options,
            partner_lines,
            '_report_expand_unfoldable_line_partner_ledger_currency_prefix_group',
            parent_level,
            matched_prefix=matched_prefix,
            parent_line_dict_id=line_dict_id,
        )
        return {
            'lines': lines,
            'offset_increment': len(lines),
            'has_more': False,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # DETAIL EXPAND: (partner, currency) → individual journal items
    # ─────────────────────────────────────────────────────────────────────────

    def _report_expand_unfoldable_line_partner_ledger_currency(
        self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None
    ):
        """Expand one (partner, currency) summary row into individual AML lines."""
        report = self.env['account.report'].browse(options['report_id'])
        markup, _model, partner_id = report._parse_line_id(line_dict_id)[-1]

        currency_id = self._parse_currency_id_from_markup(markup)
        currency = self.env['res.currency'].browse(currency_id) if currency_id else self.env.company.currency_id

        lines = []

        # ── Initial balance ───────────────────────────────────────────────
        if offset == 0 and not options.get('hide_initial_balance'):
            init_balance = self._get_initial_balance_by_currency(
                report, partner_id, currency_id, options
            )
            init_line = self._get_initial_balance_line_currency(
                report, options, line_dict_id, init_balance, currency
            )
            if init_line:
                lines.append(init_line)
                progress = {
                    col['column_group_key']: lc.get('no_format', 0)
                    for col, lc in zip(options['columns'], init_line['columns'])
                    if col['expression_label'] == 'balance'
                }

        # ── Individual AML lines ──────────────────────────────────────────
        limit = (
            report.load_more_limit + 1
            if report.load_more_limit and options['export_mode'] != 'print'
            else None
        )
        aml_results = self._get_aml_values_by_currency(
            options, partner_id, currency_id, offset=offset, limit=limit
        )

        has_more = False
        treated = 0
        next_progress = progress

        for aml in aml_results:
            if self._is_report_limit_reached(report, options, treated):
                has_more = True
                break
            new_line = self._get_report_line_move_line_currency(
                options, aml, line_dict_id, next_progress, currency
            )
            lines.append(new_line)
            next_progress = {
                col['column_group_key']: lc.get('no_format', 0)
                for col, lc in zip(options['columns'], new_line['columns'])
                if col['expression_label'] == 'balance'
            }
            treated += 1

        return {
            'lines': lines,
            'offset_increment': treated,
            'has_more': has_more,
            'progress': next_progress,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # INITIAL BALANCE (foreign currency)
    # ─────────────────────────────────────────────────────────────────────────

    def _get_initial_balance_by_currency(self, report, partner_id, currency_id, options):
        """
        Return a dict keyed by column_group_key with debit/credit/balance/amount
        for the given (partner_id, currency_id) pair before the period start,
        expressed in the transaction currency (amount_currency).
        """
        if not report.filter_date_range:
            return {cg: {} for cg in options['column_groups']}

        new_options = deepcopy(options)
        date_from = fields.Date.from_string(options['date']['date_from'])
        new_date_to = fields.Date.to_string(date_from - timedelta(days=1))
        new_options['date']['date_from'] = False
        new_options['date']['date_to'] = new_date_to
        for cg in new_options['column_groups'].values():
            cg['forced_options']['date'] = new_options['date']

        domain = []
        if partner_id:
            domain.append(('partner_id', '=', partner_id))
        if currency_id:
            domain.append(('currency_id', '=', currency_id))

        queries = []
        for cg_key, cg_options in report._split_options_per_column_group(new_options).items():
            query = report._get_report_query(cg_options, 'from_beginning', domain=domain)
            queries.append(SQL(
                """
                SELECT
                    %(column_group_key)s                                                AS column_group_key,
                    SUM(CASE WHEN account_move_line.amount_currency > 0
                             THEN  account_move_line.amount_currency
                             ELSE  0 END)                                               AS debit,
                    SUM(CASE WHEN account_move_line.amount_currency < 0
                             THEN -account_move_line.amount_currency
                             ELSE  0 END)                                               AS credit,
                    SUM(account_move_line.amount_currency)                              AS balance,
                    SUM(account_move_line.amount_currency)                              AS amount
                FROM %(table_references)s
                WHERE %(search_condition)s
                """,
                column_group_key=cg_key,
                table_references=query.from_clause,
                search_condition=query.where_clause,
            ))

        init_balance = {cg: defaultdict(float) for cg in options['column_groups']}
        if queries:
            self._cr.execute(SQL(' UNION ALL ').join(queries))
            for row in self._cr.dictfetchall():
                init_balance[row['column_group_key']] = row
        return init_balance

    def _get_initial_balance_line_currency(self, report, options, parent_line_id, init_balance, currency):
        """Build the 'Initial Balance' header line for a (partner, currency) expand."""
        columns = []
        has_non_zero = False

        for column in options['columns']:
            col_expr = column['expression_label']
            cg_key = column['column_group_key']
            col_value = init_balance.get(cg_key, {}).get(col_expr)

            if col_expr in ('debit', 'credit', 'balance', 'amount') and col_value is not None:
                if isinstance(col_value, (int, float)) and col_value != 0.0:
                    has_non_zero = True
                columns.append(
                    report._build_column_dict(col_value, column, options=options, currency=currency)
                )
            else:
                columns.append(report._build_column_dict(None, None))

        if not has_non_zero:
            return None

        return {
            'id': report._get_generic_line_id(
                None, None, parent_line_id=parent_line_id, markup='initial'
            ),
            'name': _('Initial Balance'),
            'level': 3,
            'parent_id': parent_line_id,
            'columns': columns,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # DETAIL AML QUERY & LINE RENDERING
    # ─────────────────────────────────────────────────────────────────────────

    def _get_aml_values_by_currency(self, options, partner_id, currency_id, offset=0, limit=None):
        """
        Return journal-item rows for (partner_id, currency_id) where the
        monetary values (debit, credit, balance) are expressed in
        amount_currency (the original transaction currency).
        """
        report = self.env.ref('account_reports.partner_ledger_report')
        journal_name = self.env['account.journal']._field_to_sql('journal', 'name')

        partner_clause = (
            SQL('account_move_line.partner_id = %s', partner_id)
            if partner_id
            else SQL('account_move_line.partner_id IS NULL')
        )
        currency_clause = (
            SQL('AND account_move_line.currency_id = %s', currency_id)
            if currency_id
            else SQL('')
        )

        queries = []
        for cg_key, cg_options in report._split_options_per_column_group(options).items():
            query = report._get_report_query(cg_options, 'strict_range')
            account_alias = query.left_join(
                lhs_alias='account_move_line',
                lhs_column='account_id',
                rhs_table='account_account',
                rhs_column='id',
                link='account_id',
            )
            account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
            account_name = self.env['account.account']._field_to_sql(account_alias, 'name')

            queries.append(SQL(
                """
                SELECT
                    account_move_line.id,
                    COALESCE(account_move_line.date_maturity,
                             account_move_line.date)                            AS date_maturity,
                    account_move_line.name,
                    account_move_line.ref,
                    account_move_line.company_id,
                    account_move_line.account_id,
                    account_move_line.payment_id,
                    account_move_line.partner_id,
                    account_move_line.currency_id,
                    account_move_line.amount_currency,
                    account_move_line.matching_number,
                    COALESCE(account_move_line.invoice_date,
                             account_move_line.date)                            AS invoice_date,
                    CASE WHEN account_move_line.amount_currency > 0
                         THEN  account_move_line.amount_currency
                         ELSE  0 END                                            AS debit,
                    CASE WHEN account_move_line.amount_currency < 0
                         THEN -account_move_line.amount_currency
                         ELSE  0 END                                            AS credit,
                    account_move_line.amount_currency                           AS balance,
                    account_move_line.amount_currency                           AS amount,
                    account_move.name                                           AS move_name,
                    account_move.move_type                                      AS move_type,
                    %(account_code)s                                            AS account_code,
                    %(account_name)s                                            AS account_name,
                    journal.code                                                AS journal_code,
                    %(journal_name)s                                            AS journal_name,
                    %(column_group_key)s                                        AS column_group_key,
                    0                                                           AS partial_id
                FROM %(table_references)s
                JOIN  account_move    ON account_move.id    = account_move_line.move_id
                LEFT JOIN account_journal journal ON journal.id = account_move_line.journal_id
                WHERE %(search_condition)s
                  AND %(partner_clause)s
                  %(currency_clause)s
                ORDER BY account_move_line.date, account_move_line.id
                """,
                account_code=account_code,
                account_name=account_name,
                journal_name=journal_name,
                column_group_key=cg_key,
                table_references=query.from_clause,
                search_condition=query.where_clause,
                partner_clause=partner_clause,
                currency_clause=currency_clause,
            ))

        full_query = SQL(' UNION ALL ').join(SQL('(%s)', q) for q in queries)
        if offset:
            full_query = SQL('%s OFFSET %s', full_query, offset)
        if limit:
            full_query = SQL('%s LIMIT %s', full_query, limit)

        self._cr.execute(full_query)
        return self._cr.dictfetchall()

    def _get_report_line_move_line_currency(self, options, aml, parent_line_id, progress, currency):
        """
        Render a single journal-item row with amounts in the transaction
        currency (amount_currency).
        """
        report = self.env['account.report'].browse(options['report_id'])
        caret_type = 'account.payment' if aml['payment_id'] else 'account.move.line'

        columns = []
        for column in options['columns']:
            col_expr = column['expression_label']
            cg_key = column['column_group_key']

            # Blank column for a different column group
            if cg_key != aml['column_group_key']:
                columns.append(report._build_column_dict(None, None))
                continue

            if col_expr == 'balance':
                running = progress.get(cg_key, 0)
                val = aml['balance'] + running
                columns.append(
                    report._build_column_dict(val, column, options=options, currency=currency)
                )
            elif col_expr in ('debit', 'credit', 'amount'):
                columns.append(
                    report._build_column_dict(aml[col_expr], column, options=options, currency=currency)
                )
            elif col_expr == 'amount_currency':
                # Not meaningful here – debit/credit/balance already show
                # the foreign currency amount.
                columns.append(report._build_column_dict(None, None))
            elif col_expr in aml:
                columns.append(report._build_column_dict(aml[col_expr], column, options=options))
            else:
                columns.append(report._build_column_dict(None, None))

        return {
            'id': report._get_generic_line_id(
                'account.move.line', aml['id'],
                parent_line_id=parent_line_id,
                markup=aml['partial_id'],
            ),
            'parent_id': parent_line_id,
            'name': self._format_aml_name(aml['name'], aml['ref'], aml['move_name']),
            'columns': columns,
            'caret_options': caret_type,
            'level': 3,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_currency_id_from_markup(markup):
        """
        Extract the currency ID that was embedded in the line markup string.
        The markup is 'fc_<id>' for a known partner or
        'no_partner_fc_<id>' for the unknown-partner bucket.
        Returns an int (currency id) or False.
        """
        if not isinstance(markup, str) or 'fc_' not in markup:
            return False
        try:
            cid = int(markup.split('fc_', 1)[1])
            return cid or False
        except (ValueError, IndexError):
            return False
