# -*- coding: utf-8 -*-
"""
General Ledger – Foreign Currency Display
=========================================
Extends the standard General Ledger report handler to support a
"Display Foreign Currencies" mode.

When the option is active the report:
  • Groups each account's journal items by the transaction currency
    (account_move_line.currency_id).
  • Shows Debit / Credit / Balance using amount_currency instead of the
    company-currency converted amounts.
  • Each (account, currency) pair appears as its own summary row.
  • Expanding a row shows the individual journal items for that pair,
    with a running balance in the transaction currency.
  • An Initial Balance line is shown when the date filter is a range.
"""

from collections import defaultdict
from copy import deepcopy
from datetime import timedelta

from odoo import _, fields, models
from odoo.tools import SQL


class GeneralLedgerForeignCurrencyHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    # ─────────────────────────────────────────────────────────────────────────
    # OPTIONS
    # ─────────────────────────────────────────────────────────────────────────

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['display_foreign_currency'] = (previous_options or {}).get('display_foreign_currency', False)

    # ─────────────────────────────────────────────────────────────────────────
    # TOP-LEVEL LINES GENERATOR
    # ─────────────────────────────────────────────────────────────────────────

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        if not options.get('display_foreign_currency'):
            return super()._dynamic_lines_generator(
                report, options, all_column_groups_expression_totals, warnings=warnings
            )

        account_lines = self._build_account_currency_lines(report, options)

        # Reuse the standard prefix-grouping mechanism so alphabetical
        # collapsing still works in FC mode.
        lines = report._regroup_lines_by_name_prefix(
            options,
            account_lines,
            '_report_expand_unfoldable_line_general_ledger_currency_prefix_group',
            0,
        )
        # No grand-total line: amounts are in mixed currencies and cannot be
        # meaningfully summed.
        return [(0, line) for line in lines]

    # ─────────────────────────────────────────────────────────────────────────
    # ACCOUNT SUMMARY LINES  (one row per account × currency)
    # ─────────────────────────────────────────────────────────────────────────

    def _build_account_currency_lines(self, report, options, level_shift=0):
        """Return a list of summary line dicts, one per (account, currency)."""
        groupby = {}
        self._cr.execute(self._get_query_sums_by_currency(report, options))
        for res in self._cr.dictfetchall():
            key = (res['account_id'], res['currency_id'])
            groupby.setdefault(key, defaultdict(lambda: defaultdict(float)))
            for f in ('debit', 'credit', 'balance', 'amount'):
                groupby[key][res['column_group_key']][f] += res[f]

        account_ids  = [k[0] for k in groupby if k[0] is not None]
        currency_ids = list({k[1] for k in groupby if k[1] is not None})

        accounts_map   = {a.id: a for a in self.env['account.account'].browse(account_ids)}
        currencies_map = {c.id: c for c in self.env['res.currency'].browse(currency_ids)}

        results = [
            ((accounts_map.get(aid), currencies_map.get(cid)), vals)
            for (aid, cid), vals in groupby.items()
        ]
        results.sort(key=lambda x: (
            x[0][0].code if x[0][0] else '￿',
            x[0][1].name if x[0][1] else '',
        ))

        lines = []
        for (account, currency), account_values in results:
            if not account:
                continue
            lines.append(
                self._get_report_line_account_currency(
                    options, account, currency, account_values, level_shift=level_shift
                )
            )
        return lines

    def _get_query_sums_by_currency(self, report, options) -> SQL:
        """
        Summary SQL grouped by (account_id, currency_id).
        Amounts come from amount_currency (original transaction currency).
        Mirrors _get_query_sums but without currency-table rate conversion.
        """
        queries = []
        for cg_key, cg_options in report._split_options_per_column_group(options).items():
            sum_date_scope = 'strict_range' if cg_options.get('general_ledger_strict_range') else 'from_beginning'

            query_domain = []
            if not cg_options.get('general_ledger_strict_range'):
                date_from = fields.Date.from_string(cg_options['date']['date_from'])
                fy_dates  = self.env.company.compute_fiscalyear_dates(date_from)
                query_domain += [
                    '|',
                    ('date', '>=', fy_dates['date_from']),
                    ('account_id.include_initial_balance', '=', True),
                ]

            query    = report._get_report_query(cg_options, sum_date_scope, domain=query_domain)
            date_from = options['date']['date_from']

            queries.append(SQL(
                """
                (WITH account_sums AS (
                    SELECT
                        account_move_line.account_id                                        AS account_id,
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
                    GROUP BY account_move_line.account_id, account_move_line.currency_id
                )
                SELECT *
                FROM account_sums
                WHERE  account_sums.balance      != 0
                   OR  account_sums.all_reconciled = FALSE
                   OR  account_sums.latest_date   >= %(date_from)s
                )""",
                column_group_key=cg_key,
                table_references=query.from_clause,
                search_condition=query.where_clause,
                date_from=date_from,
            ))

        return SQL(' UNION ALL ').join(queries)

    def _get_report_line_account_currency(self, options, account, currency, account_values, level_shift=0):
        """Build the summary dict for one (account, currency) row."""
        company_currency = self.env.company.currency_id
        col_currency     = currency or company_currency
        report           = self.env['account.report'].browse(options['report_id'])

        column_values = []
        for column in options['columns']:
            col_expr  = column['expression_label']
            raw_value = account_values[column['column_group_key']].get(col_expr)
            if col_expr in ('debit', 'credit', 'balance', 'amount') and raw_value is not None:
                column_values.append(
                    report._build_column_dict(raw_value, column, options=options, currency=col_currency)
                )
            else:
                column_values.append(report._build_column_dict(None, column, options=options))

        # Encode the currency into the line markup so the expand function
        # can recover it later.
        currency_id = currency.id if currency else 0
        markup      = f'fc_{currency_id}'
        line_id     = report._get_generic_line_id('account.account', account.id, markup=markup)

        unfoldable = any(
            not col_currency.is_zero(account_values[cg_key].get(f, 0.0))
            for cg_key in options['column_groups']
            for f in ('debit', 'credit')
        )

        name = account.display_name
        if currency:
            name = f'{name} [{currency.name}]'

        return {
            'id': line_id,
            'name': name,
            'columns': column_values,
            'level': 1 + level_shift,
            'unfoldable': unfoldable,
            'unfolded': line_id in options['unfolded_lines'] or options['unfold_all'],
            'expand_function': '_report_expand_unfoldable_line_general_ledger_currency',
        }

    # ─────────────────────────────────────────────────────────────────────────
    # PREFIX-GROUP EXPAND  (foreign currency mode)
    # ─────────────────────────────────────────────────────────────────────────

    def _report_expand_unfoldable_line_general_ledger_currency_prefix_group(
        self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None
    ):
        """Expand a prefix group (e.g. "100…") in foreign currency mode."""
        report          = self.env['account.report'].browse(options['report_id'])
        matched_prefix  = report._get_prefix_groups_matched_prefix_from_line_id(line_dict_id)

        prefix_domain   = [('account_id.name', '=ilike', f'{matched_prefix}%')]
        expand_options  = {
            **options,
            'forced_domain': options.get('forced_domain', []) + prefix_domain,
        }
        parent_level    = len(matched_prefix) * 2
        account_lines   = self._build_account_currency_lines(
            report, expand_options, level_shift=parent_level
        )

        for al in account_lines:
            al['id']       = report._build_subline_id(line_dict_id, al['id'])
            al['parent_id'] = line_dict_id

        lines = report._regroup_lines_by_name_prefix(
            options,
            account_lines,
            '_report_expand_unfoldable_line_general_ledger_currency_prefix_group',
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
    # DETAIL EXPAND  (account, currency) → individual journal items
    # ─────────────────────────────────────────────────────────────────────────

    def _report_expand_unfoldable_line_general_ledger_currency(
        self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None
    ):
        """Expand one (account, currency) summary row into individual AML lines."""
        report                   = self.env['account.report'].browse(options['report_id'])
        markup, _model, account_id = report._parse_line_id(line_dict_id)[-1]

        currency_id = self._parse_currency_id_from_gl_markup(markup)
        currency    = self.env['res.currency'].browse(currency_id) if currency_id else self.env.company.currency_id

        lines = []

        # ── Initial balance ────────────────────────────────────────────────
        if offset == 0:
            init_balance = self._get_initial_balance_by_currency_gl(
                report, account_id, currency_id, options
            )
            init_line = self._get_initial_balance_line_currency_gl(
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
        load_more_limit = report.load_more_limit
        limit = (load_more_limit + 1
                 if load_more_limit and options['export_mode'] != 'print'
                 else None)

        aml_results = self._get_aml_values_by_currency_gl(
            options, account_id, currency_id, offset=offset, limit=limit
        )

        has_more     = False
        treated      = 0
        next_progress = progress

        for aml in aml_results:
            if load_more_limit and options['export_mode'] != 'print' and treated == load_more_limit:
                has_more = True
                break
            new_line = self._get_report_line_move_line_currency_gl(
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
    # INITIAL BALANCE  (foreign currency)
    # ─────────────────────────────────────────────────────────────────────────

    def _get_initial_balance_by_currency_gl(self, report, account_id, currency_id, options):
        """
        Return a dict keyed by column_group_key with debit/credit/balance/amount
        for the given (account_id, currency_id) before the period start,
        expressed in the transaction currency (amount_currency).
        """
        if not report.filter_date_range:
            return {cg: {} for cg in options['column_groups']}

        new_options = deepcopy(options)
        date_from   = fields.Date.from_string(options['date']['date_from'])
        new_date_to = fields.Date.to_string(date_from - timedelta(days=1))
        new_options['date']['date_from'] = False
        new_options['date']['date_to']   = new_date_to
        for cg in new_options['column_groups'].values():
            cg['forced_options']['date'] = new_options['date']

        domain = [('account_id', '=', account_id)]
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

    def _get_initial_balance_line_currency_gl(self, report, options, parent_line_id, init_balance, currency):
        """Build the 'Initial Balance' header line for a (account, currency) expand."""
        columns     = []
        has_non_zero = False

        for column in options['columns']:
            col_expr  = column['expression_label']
            cg_key    = column['column_group_key']
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

    def _get_aml_values_by_currency_gl(self, options, account_id, currency_id, offset=0, limit=None):
        """
        Return journal-item rows for (account_id, currency_id) where the
        monetary values (debit, credit, balance) are expressed in
        amount_currency (the original transaction currency).
        """
        report        = self.env.ref('account_reports.general_ledger_report')
        journal_name  = self.env['account.journal']._field_to_sql('journal', 'name')

        domain = [('account_id', '=', account_id)]
        if currency_id:
            domain.append(('currency_id', '=', currency_id))

        queries = []
        for cg_key, cg_options in report._split_options_per_column_group(options).items():
            query        = report._get_report_query(cg_options, 'strict_range', domain=domain)
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
                    account_move_line.date,
                    account_move_line.name,
                    account_move_line.ref,
                    account_move_line.company_id,
                    account_move_line.account_id,
                    account_move_line.payment_id,
                    account_move_line.partner_id,
                    account_move_line.currency_id,
                    account_move_line.amount_currency,
                    account_move_line.matching_number,
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
                    partner.name                                                AS partner_name,
                    %(column_group_key)s                                        AS column_group_key,
                    0                                                           AS partial_id
                FROM %(table_references)s
                JOIN  account_move    ON account_move.id    = account_move_line.move_id
                LEFT JOIN account_journal journal ON journal.id   = account_move_line.journal_id
                LEFT JOIN res_partner partner     ON partner.id   = account_move_line.partner_id
                WHERE %(search_condition)s
                ORDER BY account_move_line.date, account_move_line.id
                """,
                account_code=account_code,
                account_name=account_name,
                journal_name=journal_name,
                column_group_key=cg_key,
                table_references=query.from_clause,
                search_condition=query.where_clause,
            ))

        full_query = SQL(' UNION ALL ').join(SQL('(%s)', q) for q in queries)
        if offset:
            full_query = SQL('%s OFFSET %s', full_query, offset)
        if limit:
            full_query = SQL('%s LIMIT %s', full_query, limit)

        self._cr.execute(full_query)
        return self._cr.dictfetchall()

    def _get_report_line_move_line_currency_gl(self, options, aml, parent_line_id, progress, currency):
        """
        Render a single journal-item row with amounts in the transaction
        currency (amount_currency).
        """
        report     = self.env['account.report'].browse(options['report_id'])
        caret_type = 'account.payment' if aml['payment_id'] else 'account.move.line'

        columns = []
        for column in options['columns']:
            col_expr = column['expression_label']
            cg_key   = column['column_group_key']

            if cg_key != aml['column_group_key']:
                columns.append(report._build_column_dict(None, None))
                continue

            if col_expr == 'balance':
                running = progress.get(cg_key, 0)
                val     = aml['balance'] + running
                columns.append(
                    report._build_column_dict(val, column, options=options, currency=currency)
                )
            elif col_expr in ('debit', 'credit', 'amount'):
                columns.append(
                    report._build_column_dict(aml[col_expr], column, options=options, currency=currency)
                )
            elif col_expr == 'amount_currency':
                # debit/credit/balance already carry the foreign-currency
                # value, so the amount_currency column would be redundant.
                columns.append(report._build_column_dict(None, None))
            elif col_expr in aml:
                columns.append(report._build_column_dict(aml[col_expr], column, options=options))
            else:
                columns.append(report._build_column_dict(None, None))

        # Build line name: move reference – partner (mirrors standard GL style)
        ref       = aml.get('ref') or ''
        name      = aml.get('name') or ''
        move_name = aml.get('move_name') or ''
        if ref and name:
            label = f'{ref} - {name}'
        elif ref:
            label = ref
        else:
            label = name
        if not label:
            label = move_name

        return {
            'id': report._get_generic_line_id(
                'account.move.line', aml['id'],
                parent_line_id=parent_line_id,
                markup=str(aml.get('date', '')),
            ),
            'parent_id': parent_line_id,
            'name': label or _('Draft Entry'),
            'columns': columns,
            'caret_options': caret_type,
            'level': 3,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_currency_id_from_gl_markup(markup):
        """
        Extract the currency ID embedded in a line markup string.
        The markup is 'fc_<id>' for a known account.
        Returns an int (currency id) or False.
        """
        if not isinstance(markup, str) or 'fc_' not in markup:
            return False
        try:
            cid = int(markup.split('fc_', 1)[1])
            return cid or False
        except (ValueError, IndexError):
            return False
