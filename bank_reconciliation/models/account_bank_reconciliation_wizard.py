# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountBankReconciliationWizard(models.TransientModel):
    _name = 'account.bank.reconciliation.wizard'
    _description = 'Bank Statement Line Reconciliation Wizard'

    # =========================================================================
    # FIELDS
    # =========================================================================

    st_line_id = fields.Many2one(
        comodel_name='account.bank.statement.line',
        string='Statement Line',
        required=True,
        ondelete='cascade',
    )

    reconciliation_type = fields.Selection(
        selection=[
            ('payment', 'Match Payment'),
            ('invoice', 'Match Invoice / Bill'),
            ('manual', 'Match Journal Entry'),
            ('writeoff', 'Write-off'),
        ],
        string='Reconciliation Type',
        default='payment',
        required=True,
    )

    # ── Payment matching ──────────────────────────────────────────────────────
    # Odoo 18 replaced 'posted' with 'in_process' (outstanding account not yet
    # reconciled) and 'paid' (fully cleared / non-reconcilable journal account).
    # bank_stmt_reconciled=False excludes payments already matched via our wizard.
    # expected_payment_type filters inbound (positive amount) vs outbound (negative).
    payment_id = fields.Many2one(
        comodel_name='account.payment',
        string='Payment',
        domain="[('company_id', '=', company_id), "
               "('state', 'in', ['in_process', 'paid']), "
               "('bank_stmt_reconciled', '=', False), "
               "('payment_type', '=', expected_payment_type)]",
    )

    # ── Invoice / Bill matching ───────────────────────────────────────────────
    invoice_id = fields.Many2one(
        comodel_name='account.move',
        string='Invoice / Bill',
        domain="[('company_id', '=', company_id), "
               "('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']), "
               "('state', '=', 'posted'), "
               "('payment_state', 'in', ['not_paid', 'in_payment', 'partial'])]",
    )

    # ── Manual journal entry matching ─────────────────────────────────────────
    # origin_payment_id = False  → excludes payment moves.
    # statement_line_id = False  → excludes bank statement moves.
    manual_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Journal Entry',
        domain="[('company_id', '=', company_id), "
               "('state', '=', 'posted'), "
               "('move_type', '=', 'entry'), "
               "('origin_payment_id', '=', False), "
               "('statement_line_id', '=', False)]",
    )

    # ── Write-off ─────────────────────────────────────────────────────────────
    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Account',
        domain="[('company_ids', 'in', [company_id]), ('deprecated', '=', False)]",
    )

    writeoff_label = fields.Char(
        string='Write-off Label',
        default='Write-off',
    )

    # =========================================================================
    # RELATED / COMPUTED READ-ONLY INFO FIELDS
    # =========================================================================

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='st_line_id.currency_id',
        string='Currency',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='st_line_id.company_id',
        string='Company',
    )
    transaction_amount = fields.Monetary(
        related='st_line_id.amount',
        string='Transaction Amount',
        currency_field='currency_id',
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        related='st_line_id.journal_id',
        string='Journal',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        related='st_line_id.partner_id',
        string='Partner',
    )
    payment_ref = fields.Char(
        related='st_line_id.payment_ref',
        string='Label',
    )
    st_line_date = fields.Date(
        related='st_line_id.date',
        string='Date',
    )
    is_reconciled = fields.Boolean(
        related='st_line_id.is_reconciled',
        string='Already Reconciled',
    )

    # True when the parent bank statement is in 'done' state → all fields readonly.
    is_statement_done = fields.Boolean(
        string='Statement Done',
        compute='_compute_is_statement_done',
    )

    @api.depends('st_line_id.statement_id.reconciliation_state')
    def _compute_is_statement_done(self):
        for rec in self:
            rec.is_statement_done = (
                rec.st_line_id.statement_id.reconciliation_state == 'done'
            )

    # Drives payment type filter:
    #   transaction_amount >= 0  →  'inbound'  (customer receipt / deposit)
    #   transaction_amount < 0   →  'outbound' (vendor payment / withdrawal)
    expected_payment_type = fields.Selection(
        selection=[('inbound', 'Inbound'), ('outbound', 'Outbound')],
        string='Expected Payment Type',
        compute='_compute_expected_payment_type',
    )

    @api.depends('transaction_amount')
    def _compute_expected_payment_type(self):
        for rec in self:
            rec.expected_payment_type = (
                'outbound' if (rec.transaction_amount or 0) < 0 else 'inbound'
            )

    # =========================================================================
    # DEFAULT_GET – pre-populate from matched fields when line is reconciled
    # =========================================================================

    @api.model
    def default_get(self, fields_list):
        """When the wizard is opened on an already-reconciled line, pre-populate
        the reconciliation type and the matched entity so the user can review
        what was matched (displayed in read-only mode)."""
        defaults = super().default_get(fields_list)
        st_line_id = (
            defaults.get('st_line_id')
            or self._context.get('default_st_line_id')
        )
        if not st_line_id:
            return defaults

        st_line = self.env['account.bank.statement.line'].browse(st_line_id)
        if not (st_line.is_reconciled and st_line.matched_reconciliation_type):
            return defaults

        defaults['reconciliation_type'] = st_line.matched_reconciliation_type

        if st_line.matched_payment_id:
            defaults['payment_id'] = st_line.matched_payment_id.id
        if st_line.matched_invoice_id:
            defaults['invoice_id'] = st_line.matched_invoice_id.id
        if st_line.matched_manual_move_id:
            defaults['manual_move_id'] = st_line.matched_manual_move_id.id
        if st_line.matched_writeoff_account_id:
            defaults['account_id'] = st_line.matched_writeoff_account_id.id
        if st_line.matched_writeoff_label:
            defaults['writeoff_label'] = st_line.matched_writeoff_label
        # manual_move_id is also handled via matched_manual_move_id above.

        return defaults

    # =========================================================================
    # ACTION METHODS
    # =========================================================================

    def action_reconcile(self):
        """Dispatch to the appropriate reconciliation method."""
        self.ensure_one()
        st_line = self.st_line_id

        if not st_line:
            raise UserError(_("No statement line selected."))

        if st_line.is_reconciled:
            raise UserError(_(
                "This statement line is already reconciled.\n"
                "Use the 'Reset to Draft' option before reconciling again."
            ))

        if self.is_statement_done:
            raise UserError(_(
                "The bank statement is marked as Done. "
                "No further reconciliation is allowed."
            ))

        rtype = self.reconciliation_type
        if rtype == 'payment':
            self._reconcile_with_payment()
        elif rtype == 'invoice':
            self._reconcile_with_invoice()
        elif rtype == 'manual':
            self._reconcile_with_manual_move()
        elif rtype == 'writeoff':
            self._reconcile_writeoff()
        else:
            raise UserError(_("Unknown reconciliation type: %s") % rtype)

        return {'type': 'ir.actions.act_window_close'}

    # =========================================================================
    # RECONCILIATION HELPERS
    # =========================================================================

    def _get_suspense_line(self, st_line):
        """Return the suspense (counterpart) line on the bank statement move.

        Raises UserError if no suspense line is found (already reconciled or
        the journal is not properly configured).
        """
        _liquidity_lines, suspense_lines, _other_lines = st_line._seek_for_lines()
        if not suspense_lines:
            raise UserError(_(
                "No suspense line found on statement line '%s'.\n"
                "It may have already been reconciled or the journal is not properly configured.",
                st_line.display_name,
            ))
        return suspense_lines[:1]

    def _switch_suspense_account(self, suspense_line, target_account, label=None):
        """Change the account on the suspense line to *target_account*.

        Writing directly on the account.move.line record (rather than via
        Command.clear() + Command.create() on the parent move's line_ids) avoids
        triggering account.move._synchronize_from_moves(), which enforces the
        'exactly one liquidity line' constraint and can raise a false positive
        when the counterpart account happens to equal the journal's default
        (bank/cash) account.

        ``skip_account_move_synchronization=True`` is required because
        account.move.line.write() explicitly calls
        ``self.move_id._synchronize_business_models(['line_ids'])`` at the end
        of every write (line 1750 of account_move_line.py), which would trigger
        the same _synchronize_from_moves check.  Skipping is safe here because
        _synchronize_from_moves only syncs payment_ref / partner_id / amount FROM
        the liquidity (bank) line — values we are not changing at all.
        """
        vals = {'account_id': target_account.id}
        if label:
            vals['name'] = label
        suspense_line.with_context(
            force_delete=True,
            skip_readonly_check=True,
            check_move_validity=False,
            skip_account_move_synchronization=True,
        ).write(vals)

    # -------------------------------------------------------------------------

    def _reconcile_with_payment(self):
        """Switch the suspense line to the payment's outstanding account,
        then reconcile it with the matching line on the payment journal entry."""
        self.ensure_one()

        if not self.payment_id:
            raise UserError(_("Please select a payment to match."))

        payment = self.payment_id
        st_line = self.st_line_id

        # Payments on non-reconcilable bank journals have no outstanding account.
        # The bank entry and the payment entry share the same bank account and
        # there is nothing to cross-reconcile — just mark the line as checked.
        if not payment.outstanding_account_id:
            st_line.with_context(
                force_delete=True,
                skip_readonly_check=True,
            ).write({'checked': True, 'matched_payment_id': payment.id})
            payment.bank_stmt_reconciled = True
            st_line.write({
                'matched_reconciliation_type': 'payment',
                'matched_move_id': payment.move_id.id,
            })
            return

        target_account = payment.outstanding_account_id

        payment_line = payment.move_id.line_ids.filtered(
            lambda l: l.account_id.id == target_account.id and not l.reconciled
        )
        if not payment_line:
            raise UserError(_(
                "Could not find an unreconciled journal item in the payment '%s' "
                "for account '%s'. The payment may already be fully matched.",
                payment.display_name,
                target_account.display_name,
            ))

        suspense_line = self._get_suspense_line(st_line)
        self._switch_suspense_account(suspense_line, target_account)

        new_entry = st_line.move_id.line_ids.filtered(
            lambda l: l.account_id.id == target_account.id and not l.reconciled
        )
        if not new_entry:
            raise UserError(_(
                "Could not find the journal item for account '%s' after switching. "
                "Please check the journal configuration.",
                target_account.display_name,
            ))

        (new_entry + payment_line).reconcile()

        payment.bank_stmt_reconciled = True
        st_line.write({
            'matched_payment_id': payment.id,
            'matched_reconciliation_type': 'payment',
            'matched_move_id': payment.move_id.id,
        })

    # -------------------------------------------------------------------------

    def _reconcile_with_invoice(self):
        """Switch the suspense line to the invoice receivable/payable account,
        then reconcile it with the matching line on the invoice journal entry."""
        self.ensure_one()

        if not self.invoice_id:
            raise UserError(_("Please select an invoice or bill to match."))

        invoice = self.invoice_id
        st_line = self.st_line_id

        if invoice.move_type in ('out_invoice', 'out_refund'):
            account_types = ('asset_receivable',)
        else:
            account_types = ('liability_payable',)

        invoice_line = invoice.line_ids.filtered(
            lambda l: l.account_id.account_type in account_types and not l.reconciled
        )
        if not invoice_line:
            raise UserError(_(
                "Could not find an unreconciled receivable/payable line on "
                "invoice '%s'. The invoice may already be fully paid.",
                invoice.display_name,
            ))
        invoice_line = invoice_line[:1]
        target_account = invoice_line.account_id

        suspense_line = self._get_suspense_line(st_line)
        self._switch_suspense_account(suspense_line, target_account)

        new_entry = st_line.move_id.line_ids.filtered(
            lambda l: l.account_id.id == target_account.id and not l.reconciled
        )
        if not new_entry:
            raise UserError(_(
                "Could not find the journal item for account '%s' after switching.",
                target_account.display_name,
            ))

        (new_entry + invoice_line).reconcile()

        st_line.write({
            'matched_invoice_id': invoice.id,
            'matched_reconciliation_type': 'invoice',
            'matched_move_id': invoice.id,
        })

    # -------------------------------------------------------------------------

    def _reconcile_with_manual_move(self):
        """Match the statement line against an existing posted journal entry.

        Finds the most appropriate unreconciled line in the selected move
        (prefers reconcilable accounts, falls back to any non-bank line),
        switches the suspense account to match, then reconciles if possible.
        """
        self.ensure_one()

        if not self.manual_move_id:
            raise UserError(_("Please select a journal entry to match."))

        move = self.manual_move_id
        st_line = self.st_line_id
        bank_account = st_line.journal_id.default_account_id

        candidates = move.line_ids.filtered(
            lambda l: l.account_id != bank_account and not l.reconciled
        )
        if not candidates:
            raise UserError(_(
                "No unreconciled journal items found in '%s'.",
                move.display_name,
            ))

        # Prefer lines on reconcilable accounts; otherwise take the first candidate.
        reconcilable = candidates.filtered(lambda l: l.account_id.reconcile)
        target_line = reconcilable[:1] or candidates[:1]
        target_account = target_line.account_id

        suspense_line = self._get_suspense_line(st_line)
        self._switch_suspense_account(suspense_line, target_account)

        new_entry = st_line.move_id.line_ids.filtered(
            lambda l: l.account_id.id == target_account.id and not l.reconciled
        )
        if not new_entry:
            raise UserError(_(
                "Could not find the journal item for account '%s' after switching.",
                target_account.display_name,
            ))

        if target_account.reconcile:
            (new_entry + target_line).reconcile()

        st_line.write({
            'matched_manual_move_id': move.id,
            'matched_reconciliation_type': 'manual',
            'matched_move_id': move.id,
        })

    # -------------------------------------------------------------------------

    def _reconcile_writeoff(self):
        """Create a write-off journal entry that cancels the suspense account
        and books the amount to the specified write-off account.

        A NEW, SEPARATE journal entry is created in a miscellaneous journal so
        that the original bank statement move remains clean (bank ↔ suspense).
        The sign of the write-off entry is derived directly from the existing
        suspense line — no manual sign logic required:

          amount > 0 (inbound / deposit):
              Statement:   bank DR X  |  suspense CR X
              Write-off:   suspense DR X  |  write-off CR X  (income / cancelled liability)
              Net effect:  bank DR X  |  write-off CR X

          amount < 0 (outbound / payment):
              Statement:   bank CR X  |  suspense DR X
              Write-off:   suspense CR X  |  write-off DR X  (expense / cancelled asset)
              Net effect:  bank CR X  |  write-off DR X

        If the suspense account is not reconcilable (non-standard journal
        configuration), falls back to switching the suspense line's account
        directly on the statement move — no separate entry is created, but the
        net accounting effect is identical.
        """
        self.ensure_one()

        if not self.account_id:
            raise UserError(_("Please select an account for the write-off."))

        st_line = self.st_line_id
        write_off_account = self.account_id
        suspense_line = self._get_suspense_line(st_line)
        suspense_account = suspense_line.account_id
        label = self.writeoff_label or _('Write-off')
        partner = st_line.partner_id

        if suspense_account.reconcile:
            # ── Preferred path: create a separate write-off entry ────────────
            misc_journal = self.env['account.journal'].search(
                [('type', '=', 'general'),
                 ('company_id', '=', st_line.company_id.id)],
                limit=1,
            )
            if not misc_journal:
                raise UserError(_(
                    "No miscellaneous journal found in company '%s'.\n"
                    "Please create a journal of type 'Miscellaneous' to process write-offs.",
                    st_line.company_id.display_name,
                ))

            # The write-off entry must CANCEL the suspense line (opposite side)
            # and BOOK the same amount to the write-off account (same side).
            susp_debit = suspense_line.credit   # opposite → cancels CR on suspense
            susp_credit = suspense_line.debit   # opposite → cancels DR on suspense
            wo_debit = suspense_line.debit      # same direction as original suspense
            wo_credit = suspense_line.credit    # same direction as original suspense

            writeoff_move = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': misc_journal.id,
                'date': st_line.date,
                'ref': label,
                'line_ids': [
                    (0, 0, {
                        'account_id': suspense_account.id,
                        'name': label,
                        'partner_id': partner.id,
                        'debit': susp_debit,
                        'credit': susp_credit,
                    }),
                    (0, 0, {
                        'account_id': write_off_account.id,
                        'name': label,
                        'partner_id': partner.id,
                        'debit': wo_debit,
                        'credit': wo_credit,
                    }),
                ],
            })
            writeoff_move.action_post()

            # Reconcile the two suspense lines to clear the suspense account.
            wo_susp_line = writeoff_move.line_ids.filtered(
                lambda l: l.account_id == suspense_account
            )
            if wo_susp_line:
                (suspense_line + wo_susp_line).with_context(
                    skip_account_move_synchronization=True
                ).reconcile()

            st_line.write({
                'matched_reconciliation_type': 'writeoff',
                'matched_writeoff_account_id': write_off_account.id,
                'matched_writeoff_label': label,
                'matched_writeoff_move_id': writeoff_move.id,
                'matched_move_id': writeoff_move.id,
            })

        else:
            # ── Fallback: switch account on the existing suspense line ────────
            # Used when the journal's suspense account is not reconcilable
            # (standard Odoo setup — the default Bank Suspense Account has
            # reconcile=False).  No separate move is created; the statement
            # line's own journal entry (st_line.move_id) is modified in place
            # so that it becomes bank_account ↔ write_off_account.
            self._switch_suspense_account(suspense_line, write_off_account, label=label)
            if write_off_account.reconcile:
                new_entry = st_line.move_id.line_ids.filtered(
                    lambda l: l.account_id == write_off_account and not l.reconciled
                )
                if new_entry:
                    new_entry.reconcile()

            # Use the statement line's own move as the transaction reference so
            # the user can click through to the resulting journal entry.
            st_line.write({
                'matched_reconciliation_type': 'writeoff',
                'matched_writeoff_account_id': write_off_account.id,
                'matched_writeoff_label': label,
                'matched_move_id': st_line.move_id.id,
            })
