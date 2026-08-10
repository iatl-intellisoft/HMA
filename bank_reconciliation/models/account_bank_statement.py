# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    # Both journal_id and date are computed without readonly=False in the base
    # model, so they render as read-only in form views.  Re-declare them with
    # readonly=False so users can pick a journal before adding lines and can
    # override the auto-computed date when needed.
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        compute='_compute_journal_id', store=True,
        readonly=False,
        check_company=True,
        domain="[('type', 'in', ['bank', 'cash'])]",
    )

    date = fields.Date(
        compute='_compute_date_index', store=True,
        readonly=False,
        index=True,
    )

    reconciliation_state = fields.Selection(
        selection=[
            ('under_reconciliation', 'Under Reconciliation'),
            ('done', 'Done'),
        ],
        string='Status',
        default='under_reconciliation',
        required=True,
        copy=False,
        tracking=True,
    )

    # -------------------------------------------------------------------------
    # COMPUTED BALANCE – reconciled lines only
    # -------------------------------------------------------------------------

    @api.depends('balance_start', 'line_ids.amount', 'line_ids.state', 'line_ids.is_reconciled')
    def _compute_balance_end(self):
        """Override: computed balance counts only reconciled statement lines.

        The base method counts all *posted* lines.  Here we restrict to lines
        that are both posted (state == 'posted') AND reconciled
        (is_reconciled == True) so that unmatched transactions do not inflate
        the running balance shown in the form.
        """
        for stmt in self:
            reconciled_lines = stmt.line_ids.filtered(
                lambda l: l.state == 'posted' and l.is_reconciled
            )
            stmt.balance_end = stmt.balance_start + sum(reconciled_lines.mapped('amount'))

    @api.depends('balance_end')
    def _compute_balance_end_real(self):
        """Override: keep Ending Balance in sync with Computed Balance.

        In our reconciliation flow the computed balance (reconciled lines only)
        IS the authoritative ending balance.  There is no need for the user to
        manually enter a separate figure.  By always mirroring balance_end, the
        two values are always equal and is_complete is True whenever all lines
        are reconciled.
        """
        for stmt in self:
            stmt.balance_end_real = stmt.balance_end

    # -------------------------------------------------------------------------
    # WORKFLOW ACTIONS
    # -------------------------------------------------------------------------

    def action_set_done(self):
        """Mark the bank statement as fully reconciled (Done)."""
        self.write({'reconciliation_state': 'done'})

    def action_set_draft(self):
        """Re-open a completed bank statement for further reconciliation."""
        self.write({'reconciliation_state': 'under_reconciliation'})

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def action_import_lines(self):
        """Open Odoo's built-in import wizard pre-configured for
        account.bank.statement.line, with default_statement_id and
        default_journal_id injected so imported lines attach to this
        statement automatically."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'import',
            'params': {
                'model': 'account.bank.statement.line',
                'context': {
                    'default_statement_id': self.id,
                    'default_journal_id': self.journal_id.id,
                },
            },
        }

    def action_open_statement_lines(self):
        """Open the statement lines list view filtered to this statement,
        with a Reconcile button on each unreconciled line."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Statement Lines: %s') % self.name,
            'res_model': 'account.bank.statement.line',
            'view_mode': 'list,form',
            'domain': [('statement_id', '=', self.id)],
            'context': {
                'default_statement_id': self.id,
                'default_journal_id': self.journal_id.id,
                'search_default_statement_id': self.id,
            },
            'views': [
                (self.env.ref(
                    'bank_reconciliation.view_bank_statement_line_reconcile_list'
                ).id, 'list'),
                (False, 'form'),
            ],
        }


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Set to True by our reconciliation wizard when this payment is matched to
    # a bank statement line.  Reset to False when the statement line is reset
    # via action_undo_reconciliation so the payment becomes selectable again.
    bank_stmt_reconciled = fields.Boolean(
        string='Reconciled via Bank Statement',
        default=False,
        copy=False,
        help="Indicates that this payment has been matched with a bank statement "
             "line via the Bank Reconciliation module. Cleared automatically when "
             "the statement line is reset to unreconciled.",
    )


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    # ------------------------------------------------------------------
    # Reconciliation tracking fields
    # Set by the wizard when a match is made; cleared by action_undo_reconciliation.
    # These allow the wizard to display what was matched when reopened on a
    # reconciled line (read-only review mode).
    # ------------------------------------------------------------------

    matched_reconciliation_type = fields.Selection(
        selection=[
            ('payment', 'Match Payment'),
            ('invoice', 'Match Invoice / Bill'),
            ('manual', 'Match Journal Entry'),
            ('writeoff', 'Write-off'),
        ],
        string='Reconciliation Method',
        copy=False,
        help="Type of reconciliation used to match this statement line.",
    )

    matched_payment_id = fields.Many2one(
        comodel_name='account.payment',
        string='Matched Payment',
        copy=False,
        ondelete='set null',
        help="The payment that was matched to this statement line via the "
             "Bank Reconciliation wizard.",
    )

    matched_invoice_id = fields.Many2one(
        comodel_name='account.move',
        string='Matched Invoice',
        copy=False,
        ondelete='set null',
        help="Invoice matched to this statement line via the reconciliation wizard.",
    )

    matched_manual_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Matched Journal Entry',
        copy=False,
        ondelete='set null',
        help="Journal entry matched to this statement line via the reconciliation wizard.",
    )

    matched_writeoff_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Write-off Account Used',
        copy=False,
        ondelete='set null',
        help="Write-off account used to reconcile this statement line.",
    )

    matched_writeoff_label = fields.Char(
        string='Write-off Label Used',
        copy=False,
        help="Label of the write-off entry used to reconcile this statement line.",
    )

    matched_writeoff_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Write-off Entry',
        copy=False,
        ondelete='set null',
        help="The write-off journal entry created for this statement line.",
    )

    # Single unified reference shown in the list/form for quick review.
    # Set to:
    #   payment  → payment.move_id (payment's journal entry)
    #   invoice  → the invoice itself (account.move)
    #   manual   → the selected journal entry (account.move)
    #   writeoff → the write-off entry created (account.move), or False if
    #              the fallback account-switch path was used.
    matched_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Transaction Reference',
        copy=False,
        ondelete='set null',
        readonly=True,
        help="The journal entry this statement line was reconciled against.",
    )

    # ------------------------------------------------------------------

    def action_save_new(self):
        """Fix for enterprise account_accountant's action_save_new which assumes
        default_journal_id is always in context (KeyError crash when it is not).
        Fall back to the current line's journal when the context key is absent."""
        if 'default_journal_id' not in self._context:
            self = self.with_context(default_journal_id=self.journal_id.id)
        return super().action_save_new()

    def action_undo_reconciliation(self):
        """Reset all reconciliation tracking flags, then delegate to the base undo.

        Order of operations:
        1. Clear payment bank_stmt_reconciled flag (before base undo).
        2. Call super() with skip_account_move_synchronization=True to avoid the
           'exactly one journal item involving bank/cash account' error that the
           base method would otherwise trigger by writing line_ids with
           Command.clear() + Command.create() without the skip flag.
        3. Delete any write-off journal entry we created (reconciliation is now
           removed by super(), so the entry has no open reconciled lines and can
           be drafted and deleted safely).
        4. Clear all tracking fields on the statement line.
        """
        # Step 1 – clear payment flag before the base method removes it.
        for st_line in self:
            if st_line.matched_payment_id:
                st_line.matched_payment_id.bank_stmt_reconciled = False

        # Step 2 – base undo with sync bypass.
        self_ctx = self.with_context(skip_account_move_synchronization=True)
        result = super(AccountBankStatementLine, self_ctx).action_undo_reconciliation()

        # Step 3 – delete write-off moves (reconciliation already removed above).
        for st_line in self:
            wo_move = st_line.matched_writeoff_move_id
            if wo_move and wo_move.exists():
                try:
                    if wo_move.state == 'posted':
                        wo_move.button_draft()
                    wo_move.with_context(force_delete=True).unlink()
                except Exception as exc:
                    _logger.warning(
                        "Could not delete write-off move %s during undo: %s",
                        wo_move.display_name, exc,
                    )

        # Step 4 – clear all tracking fields.
        self.write({
            'matched_payment_id': False,
            'matched_reconciliation_type': False,
            'matched_invoice_id': False,
            'matched_manual_move_id': False,
            'matched_writeoff_account_id': False,
            'matched_writeoff_label': False,
            'matched_writeoff_move_id': False,
            'matched_move_id': False,
        })

        return result

    def action_open_reconciliation_wizard(self):
        """Open the reconciliation wizard for this statement line."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reconcile Transaction'),
            'res_model': 'account.bank.reconciliation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_st_line_id': self.id,
            },
        }
