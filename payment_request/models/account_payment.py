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
    is_negative_remaining_amount = fields.Boolean(related='payment_request_id.is_negative_remaining_amount') 
    negative_remaining_amount = fields.Integer(related='payment_request_id.negative_remaining_amount')

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

   
    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        line_vals_list = super(AccountPayment, self)._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
        )
    
        if not self.payment_request_id:
            return line_vals_list
    
        for vals in line_vals_list:
            vals['payment_request_id'] = self.payment_request_id.id
    
    
        if (
            not self.payment_request_id.is_need_clearance
            and not self.payment_request_id.is_purchase
            and not self.payment_request_id.line_ids
        ):
    
            for vals in line_vals_list:
                account = self.env['account.account'].browse(vals['account_id'])
    
                if account.account_type in ('asset_receivable', 'liability_payable'):
                    vals['account_id'] = self.payment_request_id.account_id.id
                    vals['partner_id'] = False
    
            return line_vals_list
    
        if (
            not self.payment_request_id.is_need_clearance
            and not self.payment_request_id.is_purchase
            and self.payment_request_id.line_ids
        ):
    
            new_line_vals_list = []
    
            for vals in line_vals_list:
    
                account = self.env['account.account'].browse(vals['account_id'])
    
                if account.account_type in ('asset_receivable', 'liability_payable'):
    
                    total = sum(
                        l.price_subtotal
                        for l in self.payment_request_id.line_ids
                    ) or 1.0
    
                    original_balance = vals['balance']
                    original_amount_currency = vals['amount_currency']
    
                    for line in self.payment_request_id.line_ids:
    
                        ratio = line.price_subtotal / total
    
                        new_line_vals_list.append({
                            'name': line.name,
                            'date_maturity': self.date,
                            'account_id': line.expense_account_id.id,
                            'partner_id': False,
                            'currency_id': vals['currency_id'],
                            'amount_currency': original_amount_currency * ratio,
                            'balance': original_balance * ratio,
                            'analytic_account_id': line.analytic_account_id.id if line.analytic_account_id else False,
                            'payment_request_id': self.payment_request_id.id,
                        })
    
                else:
                    new_line_vals_list.append(vals)
    
            return new_line_vals_list
    
        return line_vals_list
        
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
            if self.payment_request_id.is_negative_remaining_amount == True:
                self.payment_request_id.is_negative_remaining_amount = False
            else:                
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
                if self.is_negative_remaining_amount == True:
                    rec['amount'] = custody_defaults.negative_remaining_amount
                else:                 
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
