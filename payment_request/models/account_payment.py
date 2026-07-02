# -*- coding: utf-8 -*-

from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    bank_transaction_notification = fields.Binary(string="اشعار العملية") 
    bankak_transaction_number = fields.Char(string="رقم العملية") 

    payment_request_id = fields.Many2one(
        'payment.request', string="Payments", copy=False, )
    custody_clearance_id = fields.Many2one(
        'custody.clearance', string="Custody Clearance", copy=False, )
    is_need_clearance = fields.Boolean(string="Need Clearance", related='payment_request_id.is_need_clearance')

    destination_account_id = fields.Many2one('account.account', compute='_compute_destination_account_id',
                                             readonly=True)

    # journal_id = fields.Many2one('account.journal', compute='_compute_journal_id',
    #                              readonly=True)

    # custody_clearance_id
    def _synchronize_from_moves(self, changed_fields):
        if self.payment_request_id and self.payment_request_id.is_need_clearance:
            return super(AccountPayment, self)._synchronize_from_moves(changed_fields)
        else:
            if self._context.get('skip_account_move_synchronization'):
                return

            for pay in self.with_context(skip_account_move_synchronization=True):

                # After the migration to 14.0, the journal entry could be shared between the account.payment and the
                # account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
                if pay.move_id.statement_line_id:
                    continue

                move = pay.move_id
                move_vals_to_write = {}
                payment_vals_to_write = {}

                if 'journal_id' in changed_fields:
                    if pay.journal_id.type not in ('bank', 'cash'):
                        raise UserError(_("A payment must always belongs to a bank or cash journal."))

                if 'line_ids' in changed_fields:
                    all_lines = move.line_ids
                    liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()
                    for rec in counterpart_lines:
                        if rec.account_id.account_type == 'asset_receivable':
                            partner_type = 'customer'
                        else:
                            partner_type = 'supplier'

                        liquidity_amount = liquidity_lines.amount_currency

                        move_vals_to_write.update({
                            'currency_id': liquidity_lines.currency_id.id,
                            # 'partner_id': liquidity_lines.partner_id.id,
                        })
                        payment_vals_to_write.update({
                            'amount': abs(liquidity_amount),
                            'payment_type': 'inbound' if liquidity_amount > 0.0 else 'outbound',
                            'partner_type': partner_type,
                            'currency_id': liquidity_lines.currency_id.id,
                            'destination_account_id': rec.account_id.id,
                            # 'partner_id': liquidity_lines.partner_id.id,
                            # 'journal_id':pay.custody_clearance_id.journal_id.id
                        })
                move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
                pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))

    def _seek_for_lines(self):
        if self.payment_request_id and self.payment_request_id.is_need_clearance:
            return super(AccountPayment, self)._seek_for_lines()
        else:
            liquidity_lines = self.env['account.move.line']
            counterpart_lines = self.env['account.move.line']
            writeoff_lines = self.env['account.move.line']

            for line in self.move_id.line_ids:
                if line.account_id in (
                        self.journal_id.default_account_id,
                        self.outstanding_account_id,
                        self.destination_account_id,
                ):
                    liquidity_lines += line
                elif line.account_id.account_type in (
                        'asset_receivable', 'liability_payable') or line.account_id.account_type not in (
                        'asset_receivable', 'liability_payable') or line.partner_id == line.company_id.partner_id:
                    counterpart_lines += line
                else:
                    writeoff_lines += line

            return liquidity_lines, counterpart_lines, writeoff_lines

    # def _synchronize_to_moves(self, changed_fields):
    #     ''' Update the account.move regarding the modified account.payment.
    #     :param changed_fields: A list containing all modified fields on account.payment.
    #     '''
    #     if self._context.get('skip_account_move_synchronization'):
    #         return

    #     if not any(field_name in changed_fields for field_name in (
    #             'date', 'amount', 'payment_type', 'partner_type', 'payment_reference', 'is_internal_transfer',
    #             'currency_id', 'partner_id', 'destination_account_id', 'partner_bank_id',
    #     )):
    #         return

    #     for pay in self.with_context(skip_account_move_synchronization=True):
    #         liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

    #         # Make sure to preserve the write-off amount.
    #         # This allows to create a new payment with custom 'line_ids'.

    #         if writeoff_lines:
    #             writeoff_amount = sum(writeoff_lines.mapped('amount_currency'))
    #             counterpart_amount = counterpart_lines['amount_currency']
    #             if writeoff_amount > 0.0 and counterpart_amount > 0.0:
    #                 sign = 1
    #             else:
    #                 sign = -1

    #             write_off_line_vals = {
    #                 'name': writeoff_lines[0].name,
    #                 'amount': writeoff_amount * sign,
    #                 'account_id': writeoff_lines[0].account_id.id,
    #             }
    #         else:
    #             write_off_line_vals = {}

    #         line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)

    #         line_ids_commands = [
    #             (1, liquidity_lines.id, line_vals_list[0]),
    #             (1, counterpart_lines.id, line_vals_list[1]),
    #         ]

    #         for line in writeoff_lines:
    #             line_ids_commands.append((2, line.id))

    #         if writeoff_lines:
    #             line_ids_commands.append((0, 0, line_vals_list[2]))

    #         # Update the existing journal items.
    #         # If dealing with multiple write-off lines, they are dropped and a new one is generated.

    #         pay.move_id.write({
    #             'partner_id': pay.partner_id.id,
    #             'currency_id': pay.currency_id.id,
    #             'partner_bank_id': pay.partner_bank_id.id,
    #             'line_ids': line_ids_commands,
    #         })

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        ''' inherit to do payment request Edit
        '''
        new_line_vals_list = []
        line_vals_list = super(AccountPayment, self)._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals, force_balance=force_balance)
        count = 0
        write_off_line_vals = write_off_line_vals or {}
        if self.payment_request_id and not self.payment_request_id.is_need_clearance and not self.payment_request_id.is_purchase:
            for res in line_vals_list:
                acc_type = " "
                if type(res) is dict:
                    if res.get('account_id', ' '):
                        acc_type = self.env['account.account'].browse(res['account_id']).account_type
                res['payment_request_id'] = self.payment_request_id.id
                if acc_type in ('asset_receivable', 'liability_payable') or self.partner_id == self.company_id.partner_id:
                    # Compute amounts.
                    write_off_amount = write_off_line_vals.get('total_amount', 0.0)

                    if self.payment_type == 'inbound':
                        # Receive money.
                        counterpart_amount = -self.payment_request_id.total_amount
                        write_off_amount *= -1
                    elif self.payment_type == 'outbound':
                        # Send money.
                        counterpart_amount = self.payment_request_id.total_amount
                    else:
                        counterpart_amount = 0.0
                        write_off_amount = 0.0
                    counterpart_amount_currency = counterpart_amount
                    write_off_balance = self.currency_id._convert(write_off_amount, self.company_id.currency_id,
                                                                  self.company_id,
                                                                  self.date)
                    write_off_amount_currency = write_off_amount
                    currency_id = self.currency_id.id
                    total = sum(line.price_subtotal for line in self.payment_request_id.line_ids) or 1.0
                    for line in self.payment_request_id.line_ids:
                        line_share = line.price_subtotal / total
                        line_write_off = write_off_balance * line_share
                        balance = self.currency_id._convert(
                            line.price_subtotal,
                            self.company_id.currency_id,
                            self.company_id,
                            self.date
                        )
                        debit = line_write_off if  line_write_off > 0 else 0.0
                        credit = - line_write_off if  line_write_off < 0 else 0.0

                        line_vals_list.append({
                            'name': line.name,
                            'date_maturity': self.date,
                            'amount_currency': counterpart_amount_currency * line_share + write_off_amount_currency * line_share,
                            'currency_id': currency_id,
                            'debit': debit,
                            'credit': credit,
                            'partner_id': '',
                            'account_id': line.expense_account_id.id,
                            'analytic_account_id': line.analytic_account_id.id if line.analytic_account_id else False,
                            # 'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)] if line.analytic_tag_ids else False,
                            'payment_request_id': self.payment_request_id.id
                        })
                else:
                    new_line_vals_list.append(res)
            import logging
            _logger = logging.getLogger(__name__)
            
            total_debit = sum(l.get('debit', 0.0) for l in new_line_vals_list)
            total_credit = sum(l.get('credit', 0.0) for l in new_line_vals_list)
            
            _logger.warning("================================")
            _logger.warning("Payment Amount: %s", self.amount)
            _logger.warning("Debit: %s", total_debit)
            _logger.warning("Credit: %s", total_credit)
            _logger.warning("write_off_amount = %s", write_off_amount)
            _logger.warning("write_off_balance = %s", write_off_balance)
            
            for line in new_line_vals_list:
                _logger.warning(line)
                _logger.warning(
                    "subtotal=%s share=%s line_write_off=%s",
                    line.price_subtotal,
                    line_share,
                    line_write_off,
                )
            return new_line_vals_list
            

        else:
            return line_vals_list

    # def _prepare_move_line_default_vals(self, write_off_line_vals=None):
    #     ''' inherit to do payment request Edit
    #     '''
    #     self.ensure_one()
    #     write_off_line_vals = write_off_line_vals or {}

    #     if not self.journal_id.payment_debit_account_id or not self.journal_id.payment_credit_account_id:
    #         raise UserError(_(
    #             "You can't create a new payment without an outstanding payments/receipts account set on the %s journal.",
    #             self.journal_id.display_name))

    #     # Compute amounts.
    #     write_off_amount = write_off_line_vals.get('amount', 0.0)

    #     if self.payment_type == 'inbound':
    #         # Receive money.
    #         counterpart_amount = -self.amount
    #         write_off_amount *= -1
    #     elif self.payment_type == 'outbound':
    #         # Send money.
    #         counterpart_amount = self.amount
    #     else:
    #         counterpart_amount = 0.0
    #         write_off_amount = 0.0

    #     balance = self.currency_id._convert(counterpart_amount, self.company_id.currency_id, self.company_id, self.date)
    #     counterpart_amount_currency = counterpart_amount
    #     write_off_balance = self.currency_id._convert(write_off_amount, self.company_id.currency_id, self.company_id,
    #                                                   self.date)
    #     write_off_amount_currency = write_off_amount
    #     currency_id = self.currency_id.id

    #     if self.is_internal_transfer:
    #         if self.payment_type == 'inbound':
    #             liquidity_line_name = _('Transfer to %s', self.journal_id.name)
    #         else:  # payment.payment_type == 'outbound':
    #             liquidity_line_name = _('Transfer from %s', self.journal_id.name)
    #     else:
    #         liquidity_line_name = self.payment_reference

    #     # Compute a default label to set on the journal items.

    #     payment_display_name = {
    #         'outbound-customer': _("Customer Reimbursement"),
    #         'inbound-customer': _("Customer Payment"),
    #         'outbound-supplier': _("Vendor Payment"),
    #         'inbound-supplier': _("Vendor Reimbursement"),
    #     }

    #     if self.payment_request_id and not self.payment_request_id.is_need_clearance and not self.payment_request_id.is_purchase:
    #         default_line_name = self.env['account.move.line']._get_default_line_name(
    #             _("Internal Transfer") if self.is_internal_transfer else payment_display_name[
    #                 '%s-%s' % (self.payment_type, self.partner_type)],
    #             self.amount,
    #             self.currency_id,
    #             self.date,
    #             partner=self.partner_id,
    #         )

    #         line_vals_list = [
    #             # Liquidity line.
    #             {
    #                 'name': liquidity_line_name or default_line_name,
    #                 'date_maturity': self.date,
    #                 'amount_currency': -counterpart_amount_currency,
    #                 'currency_id': currency_id,
    #                 'debit': balance < 0.0 and -balance or 0.0,
    #                 'credit': balance > 0.0 and balance or 0.0,
    #                 'partner_id': self.partner_id.id,
    #                 'account_id': self.journal_id.payment_debit_account_id.id if balance < 0.0 else self.journal_id.payment_credit_account_id.id,
    #                 'payment_request_id': self.payment_request_id.id
    #             }]
    #         # Receivable / Payable.
    #         for line in self.payment_request_id.line_ids:
    #             default_line_name = self.env['account.move.line']._get_default_line_name(
    #                 _("Internal Transfer") if self.is_internal_transfer else payment_display_name[
    #                     '%s-%s' % (self.payment_type, self.partner_type)],
    #                 line.price_subtotal,
    #                 self.currency_id,
    #                 self.date,
    #                 partner=self.partner_id,
    #             )

    #             balances = self.currency_id._convert(line.price_subtotal, self.company_id.currency_id, self.company_id,
    #                                                  self.date)
    #             line_vals_list += {
    #                                   'name': self.payment_reference or default_line_name,
    #                                   'date_maturity': self.date,
    #                                   'amount_currency': counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0,
    #                                   'currency_id': currency_id,
    #                                   'debit': balances + write_off_balance > 0.0 and balances + write_off_balance or 0.0,
    #                                   'credit': balances + write_off_balance < 0.0 and -balances - write_off_balance or 0.0,
    #                                   'partner_id': self.partner_id.id,
    #                                   'account_id': line.expense_account_id.id,
    #                                   # 'tax_ids': [(6, 0, line.tax_ids.ids)] if line.tax_ids else False,
    #                                   'payment_request_id': self.payment_request_id.id

    #                               },

    #         if write_off_balance:
    #             # Write-off line.
    #             line_vals_list.append({
    #                 'name': write_off_line_vals.get('name') or default_line_name,
    #                 'amount_currency': -write_off_amount_currency,
    #                 'currency_id': currency_id,
    #                 'debit': write_off_balance < 0.0 and -write_off_balance or 0.0,
    #                 'credit': write_off_balance > 0.0 and write_off_balance or 0.0,
    #                 'partner_id': self.partner_id.id,
    #                 'account_id': write_off_line_vals.get('account_id'),
    #                 'payment_request_id': self.payment_request_id.id

    #             })
    #         return line_vals_list
    #     else:
    #         return super(AccountPayment, self)._prepare_move_line_default_vals(write_off_line_vals)

    def action_validate_custody_payment(self):
        active_ids = self._context.get('active_ids', []) or []
        active_model = self._context.get('active_model')
        close_custody = self._context.get('close', False)
        prev_custody = self.env['payment.request'].search([('employee_id','=',self.payment_request_id.employee_id.id),('state','=','paid'),('is_need_clearance','=',True)],limit=1)
        if  active_model == 'payment.request':
            if prev_custody:                
                prev_custody.state = 'close'
                self.payment_request_id.base_amount = self.payment_request_id.amount + prev_custody.remaining_amount 
                self.payment_request_id.write({'remaining_amount':  self.payment_request_id.base_amount})
            else:
                self.payment_request_id.base_amount = self.payment_request_id.amount 
                self.payment_request_id.write({'remaining_amount': self.payment_request_id.amount})
   

        for payment in self:
            # if payment.state == 'draft':
            payment.action_post()
            payment.action_validate()

        if active_model == 'custody.clearance':            
            self.payment_request_id.remaining_amount = self.payment_request_id.remaining_amount - self.custody_clearance_id.total_amount  
            self.custody_clearance_id.request_remaining_amount = self.payment_request_id.remaining_amount 
            if  self.payment_request_id.remaining_amount == 0:
                self.payment_request_id.state = 'close'
        if active_model == 'payment.request' and close_custody:

            # self.payment_request_id.write({'state': 'close'})

            return {
                'type': 'ir.actions.act_window',
                'name': 'Custody Payments',
                'res_model': 'account.payment',
                'view_mode': 'list,form',
                'views': [
                    (self.env.ref('account.view_account_payment_tree').id, 'list'),
                    (False, 'form')
                ],
                'context': {
                    'search_default_payment_request_id': self.payment_request_id.id,
                    'create': 0
                },
                'domain': [
                    ('payment_request_id', '=', self.payment_request_id.id)
                ]
            }

        elif active_model == 'payment.request' and not close_custody:
            self.payment_request_id.write({'state': 'paid'})

        elif active_model == 'custody.clearance':
            self.env['custody.clearance'].browse(active_ids).write({
                'state': 'done'
            })

        return True

    @api.model
    def default_get(self, fields):
        rec = super(AccountPayment, self).default_get(fields)
        active_ids = self._context.get('active_ids', []) or []
        active_model = self._context.get('active_model')
        clearance_defaults = False
        custody_defaults = False
        partner_type = ''
        payment_type = ''
        if active_model == 'custody.clearance':
            clearance_defaults = self.env['custody.clearance'].browse(active_ids)
            rec['amount'] = abs(clearance_defaults.payment_amount)
            if clearance_defaults.payment_amount < 0.0:
                partner_type = 'supplier'
                payment_type = 'outbound'
            else:
                partner_type = 'customer'
                # payment_type = 'inbound'
                payment_type = 'outbound'

        elif active_model == 'payment.request':
            custody_defaults = self.env['payment.request'].browse(active_ids)
            if custody_defaults.is_need_clearance:
                rec['amount'] = custody_defaults.amount
            else:
                rec['amount'] = custody_defaults.total_amount
            if self._context.get("close"):
                if custody_defaults.balance < 0.0:
                    partner_type = 'supplier'
                    payment_type = 'outbound'
                else:
                    partner_type = 'customer'
                    payment_type = 'inbound'
            else:
                payment_type = 'outbound'
                partner_type = 'supplier'

        if active_model == 'custody.clearance':
            if custody_defaults or clearance_defaults:
                rec.update({'destination_account_id': custody_defaults[0].account_id.id if custody_defaults \
                    else clearance_defaults[0].request_id.account_id.id,
                            'memo': custody_defaults[0].name if custody_defaults \
                                else clearance_defaults[0].sequence or False,
                            'payment_type': payment_type if custody_defaults else payment_type,
                            'partner_type': partner_type if custody_defaults else partner_type,
                            'payment_request_id': custody_defaults[0].id if custody_defaults \
                                else clearance_defaults[0].request_id.id or False,
                            'custody_clearance_id': clearance_defaults[0].id if clearance_defaults else False,
                            # 'journal_id': custody_defaults[0].journal_id.id if custody_defaults else clearance_defaults[
                            #     0].journal_id.id if clearance_defaults else False,
                            'currency_id': custody_defaults[0].currency_id.id if custody_defaults \
                                else clearance_defaults[0].currency_id.id or False,
                            'partner_id': custody_defaults[0].partner_id.id if custody_defaults \
                                else clearance_defaults[0].partner_id.id or False,
                            'bankak_transaction_number': self.bankak_transaction_number if self.bankak_transaction_number else False, 
                            'bank_transaction_notification': self.bank_transaction_notification if self.bank_transaction_notification else False,

                            # 'department_id': custody_defaults[0].department_id.id if custody_defaults \
                            #     else clearance_defaults[0].department_id.id or False,
                            })

                if self._context.get("close"):
                    rec['amount'] = abs(custody_defaults.total_amount)
        else:
            if custody_defaults or clearance_defaults:
                rec.update({'destination_account_id': custody_defaults[0].account_id.id if custody_defaults \
                    else clearance_defaults[0].request_id.account_id.id,
                            'memo': custody_defaults[0].name if custody_defaults \
                                else clearance_defaults[0].sequence or False,
                            'payment_type': payment_type if custody_defaults else payment_type,
                            'partner_type': partner_type if custody_defaults else partner_type,
                            'payment_request_id': custody_defaults[0].id if custody_defaults \
                                else clearance_defaults[0].request_id.id or False,
                            'custody_clearance_id': clearance_defaults[0].id if clearance_defaults else False,
                            'journal_id': custody_defaults[0].journal_id.id if custody_defaults else clearance_defaults[
                                0].journal_id.id if clearance_defaults else False,
                            'currency_id': custody_defaults[0].currency_id.id if custody_defaults \
                                else clearance_defaults[0].currency_id.id or False,
                            'partner_id': custody_defaults[0].partner_id.id if custody_defaults \
                                else clearance_defaults[0].partner_id.id or False,
                            # 'department_id': custody_defaults[0].department_id.id if custody_defaults \
                            #     else clearance_defaults[0].department_id.id or False,
                            })

                if self._context.get("close"):
                    rec['amount'] = abs(custody_defaults.total_amount)

        return rec

    def action_post(self):
        rec = super(AccountPayment, self).action_post()

        for rec in self:
            if rec.payment_request_id and not rec.custody_clearance_id:
                if rec.payment_request_id.state == 'wait_payment':
                    rec.payment_request_id.write({'state': 'paid'})
            elif rec.custody_clearance_id:
                if rec.custody_clearance_id.state == 'finance_approval':
                    rec.custody_clearance_id.write({'state': 'done'})
                    if not rec.custody_clearance_id.request_id.is_renewable:
                        rec.custody_clearance_id.request_id.write({'state': 'close'})
            if rec.payment_request_id:
                if rec.payment_request_id.state == 'close':
                    # self._context.get("close") == True:
                    rec.payment_request_id.write({'state': 'close'})
                else:
                    rec.payment_request_id.write({'state': 'paid'})
                    user_id = None
                    if not rec.payment_request_id.employee_id.user_id.id:
                        user_id = self.env.user.id
                    else:
                        user_id = rec.payment_request_id.employee_id.user_id.id
                    if rec.is_need_clearance == True:
                        activity = self.env['mail.activity'].create({
                            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                            # 'summary': summary,
                            'date_deadline': self.payment_request_id.date_clearance,
                            'user_id': user_id,
                            'res_id': self.payment_request_id.id,
                            'res_model_id': self.env['ir.model'].search([('model', '=', 'payment.request')],
                                                                        limit=1).id,
                        })

        return rec

    @api.depends('move_id', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        if self.payment_request_id:
            self.destination_account_id = self.payment_request_id.account_id.id

        else:
            return super(AccountPayment, self)._compute_destination_account_id()

    @api.onchange('partner_id')
    def onch_partner_record(self):
        if self.payment_request_id:
            self.destination_account_id = self.payment_request_id.account_id.id
