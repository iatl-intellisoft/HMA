from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    is_internal_transfer = fields.Boolean(
        string="Internal Transfer",
        default=False,
        tracking=True,
        help="Check this to record a transfer between two of your own journals (bank/cash accounts).",
    )
    # No check_company here: we intentionally allow journals from sibling branches
    # of the same root company (parent/child hierarchy).
    destination_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Destination Journal',
        help="The journal where the transferred funds will be received. "
             "Journals from all branches of the same company group are available.",
    )
    # Computed list of journals valid as a destination (all branches of the root company,
    # any bank/cash journal except the source journal itself).
    available_destination_journal_ids = fields.Many2many(
        comodel_name='account.journal',
        compute='_compute_available_destination_journal_ids',
    )

    # -------------------------------------------------------------------------
    # ONCHANGE
    # -------------------------------------------------------------------------

    @api.onchange('is_internal_transfer')
    def _onchange_is_internal_transfer(self):
        if self.is_internal_transfer:
            self.partner_id = self.company_id.partner_id
            self.payment_type = 'outbound'
            self.partner_type = 'customer'
        else:
            self.destination_journal_id = False

    @api.onchange('journal_id')
    def _onchange_journal_clear_destination(self):
        """Clear destination journal if it becomes the same as the source."""
        if self.destination_journal_id and self.destination_journal_id == self.journal_id:
            self.destination_journal_id = False

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('is_internal_transfer', 'journal_id', 'company_id')
    def _compute_available_destination_journal_ids(self):
        """
        Return all bank/cash journals reachable from the current company's branch tree,
        excluding the source journal itself.

        When logged in as a parent company (or any branch), every sibling and child
        branch journal is included so that cross-branch transfers are possible.
        """
        for pay in self:
            if not pay.is_internal_transfer:
                pay.available_destination_journal_ids = self.env['account.journal']
                continue

            # Walk up to the root company then search all its descendants
            root = (pay.company_id.root_id or pay.company_id)
            journals = self.env['account.journal'].search([
                ('type', 'in', ('bank', 'cash')),
                ('company_id', 'child_of', root.id),
            ])
            # Must have at least one inbound payment method (it will receive money)
            journals = journals.filtered('inbound_payment_method_line_ids')
            # Exclude the source journal
            pay.available_destination_journal_ids = journals.filtered(
                lambda j: j.id != pay.journal_id.id
            )

    @api.depends('journal_id', 'partner_id', 'partner_type', 'is_internal_transfer')
    def _compute_destination_account_id(self):
        """
        Override to use the transfer account for internal transfers.

        For both same-company and cross-branch transfers every company in a branch
        group typically points at the same transfer account record, so the debit
        (source) and credit (destination) entries land on the same account and can
        be reconciled automatically.
        """
        internal_transfers = self.filtered('is_internal_transfer')
        regular_payments = self - internal_transfers

        if regular_payments:
            super(AccountPayment, regular_payments)._compute_destination_account_id()

        for pay in internal_transfers:
            transfer_account = pay.company_id.transfer_account_id
            if not transfer_account:
                raise UserError(_(
                    "No transfer account found on company '%s'. "
                    "Please configure it in Accounting > Configuration > Settings.",
                    pay.company_id.name,
                ))
            pay.destination_account_id = transfer_account

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def action_post(self):
        """Override to create a paired inbound payment for internal transfers."""
        res = super().action_post()

        for pay in self.filtered(
            lambda p: p.is_internal_transfer
            and p.destination_journal_id
            and not p.paired_internal_transfer_payment_id
        ):
            paired = pay._create_paired_internal_transfer_payment()
            # Cross-link both payments
            pay.write({'paired_internal_transfer_payment_id': paired.id})
            paired.write({'paired_internal_transfer_payment_id': pay.id})
            # Post the paired payment; paired_internal_transfer_payment_id is already
            # set so the filter above will not recurse and create a third payment.
            paired.action_post()

        return res

    def _create_paired_internal_transfer_payment(self):
        """
        Create the mirrored inbound payment on the destination journal.

        When the destination journal belongs to a different branch, the payment is
        created in that branch's company context so that company-dependent fields
        (outstanding account, sequence, …) are resolved correctly for that entity.
        """
        self.ensure_one()
        dst_company = self.destination_journal_id.company_id or self.company_id
        return self.env['account.payment'].with_company(dst_company).create({
            'journal_id': self.destination_journal_id.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'amount': self.amount,
            'date': self.date,
            'memo': self.memo,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'is_internal_transfer': True,
            'destination_journal_id': self.journal_id.id,
            'company_id': dst_company.id,
        })

    def button_open_paired_transfer(self):
        """Stat button: navigate to the paired internal transfer payment."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Paired Transfer'),
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': self.paired_internal_transfer_payment_id.id,
        }
