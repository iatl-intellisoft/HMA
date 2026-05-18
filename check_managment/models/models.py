# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError, ValidationError

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


class AccountChecksFollowup(models.Model):
    _name = 'account.checks.followup'
    _rec_name = 'payment_id'
    _inherit = 'mail.thread'

    payment_id = fields.Many2one('account.payment', string='Payment', track_visibility='always', )
    payment_type = fields.Selection(
        [('outbound', 'Send Money'), ('inbound', 'Receive Money'), ('transfer', 'Internal Transfer')],
        related='payment_id.payment_type', string='Payment Type')
    partner_type = fields.Selection(related='payment_id.partner_type', string='Partner Type')
    state = fields.Selection(
        [('under-collection', 'Under Collection'), ('outstanding', 'Outstanding'), ('paid', 'Paid'),
         ('deposited', 'Deposited'), ('returned', 'Returned'), ('closed', 'Closed')], 'State',
        track_visibility='always', default='under-collection')
    vendor_state = fields.Selection(related="state")
    customer_state = fields.Selection(related="state")
    partner_id = fields.Many2one('res.partner', store=True, related='payment_id.partner_id', string='Partner',
                                 track_visibility='always', )
    journal_id = fields.Many2one('account.journal', store=True, related='payment_id.journal_id', string='Journal',
                                 track_visibility='always', )
    amount = fields.Monetary(related='payment_id.amount', store=True, string='Amount', track_visibility='always', )
    currency_id = fields.Many2one('res.currency', store=True, related="payment_id.currency_id",
                                  track_visibility='always', string='Currency',
                                  default=lambda self: self.env.user.company_id.currency_id)
    check_no = fields.Integer(string='Check Number', track_visibility='always', )
    move_id = fields.Many2one('account.move', 'Move')
    beneficiary = fields.Char(string="Beneficiary", related='payment_id.beneficiary', store=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    post_entry = fields.Boolean(string="Post Check Followup Entry", related='company_id.post_entry')
    move_ids = fields.One2many('account.move', 'check_followup_id', string='Moves', )

    # @api.multi
    def check_followup_post(self, move_id):
        if self.post_entry:
            move_id.post()

    def withdrawn(self):
        for rec in self:
            create_move = self.env['account.move'].create({'name': "Withdrawn Check OF " + rec.payment_id.name,
                                                           'journal_id': self.journal_id.id,
                                                           'date': rec.payment_id.date,
                                                           'check_followup_id': rec.id})

            move_line_id1 = False
            move_line_id2 = False
            if rec.payment_id.partner_type == 'customer':
                move_line_id1 = {'account_id': rec.journal_id.check_undercollection_account_id.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': 0,
                                 'credit': rec.amount}

                move_line_id2 = {'account_id': rec.journal_id.default_account_id.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': rec.amount,
                                 'credit': 0}

                self.check_followup_post(create_move)
                rec.state = 'deposited'

            if rec.payment_id.partner_type == 'supplier':
                move_line_id1 = {'account_id': rec.journal_id.check_outstanding_account_id.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': rec.amount,
                                 'credit': 0}

                move_line_id2 = {'account_id': rec.journal_id.default_account_id.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': 0,
                                 'credit': rec.amount}

                rec.state = 'paid'

            create_move.line_ids = [(0, 0, move_line_id1), (0, 0, move_line_id2)]

            rec.check_followup_post(create_move)
            rec.message_post(body=_("Journal Entry created <strong>  %s </strong>") % create_move.name)

    def close(self):
        for rec in self:
            create_move = self.env['account.move'].create({'name': "Close Check OF " + rec.payment_id.name,
                                                           'journal_id': self.journal_id.id,
                                                           'date': rec.payment_id.date,
                                                           'check_followup_id': rec.id})

            move_line_id1 = False
            move_line_id2 = False
            if rec.payment_id.partner_type == 'customer':
                move_line_id1 = {'account_id': rec.payment_id.company_id.account_receivable.id,
                                 # 'account_id':rec.partner_id.property_account_receivable_id.id ,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': rec.amount,
                                 'partner_id': rec.partner_id.id,
                                 'credit': 0}

                move_line_id2 = {'account_id': rec.partner_id.property_account_receivable_id.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': 0,
                                 'credit': rec.amount}
                self.check_followup_post(create_move)

            if rec.payment_id.partner_type == 'supplier':
                move_line_id1 = {'account_id': rec.payment_id.company_id.account_payable.id,
                                 # 'account_id':rec.partner_id.property_account_payable_id.id ,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': 0,
                                 # 'partner_id' : rec.partner_id.id,
                                 'credit': rec.amount}

                move_line_id2 = {'account_id': rec.partner_id.property_account_payable_id.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': rec.amount,
                                 'partner_id': rec.partner_id.id,
                                 'credit': 0}

            create_move.line_ids = [(0, 0, move_line_id1), (0, 0, move_line_id2)]
            # add new field move_id (technical field not visible in view) store same accounts Entry in it
            self.move_id = create_move
            rec.state = 'closed'
            rec.check_followup_post(create_move)
            rec.message_post(body=_("Journal Entry created <strong>  %s </strong>") % create_move.name)

    def returned(self):
        # make journal Entry and change state to return
        for rec in self:

            create_move = self.env['account.move'].create({'name': "Returned Check OF " + rec.payment_id.name,
                                                           'journal_id': self.journal_id.id,
                                                           'date': rec.payment_id.date,
                                                           'check_followup_id': rec.id})

            move_line_id1 = False
            move_line_id2 = False
            if rec.payment_id.partner_type == 'customer':
                move_line_id1 = {'account_id': rec.journal_id.default_account_id.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': 0,
                                 'credit': rec.amount}

                move_line_id2 = {'account_id': rec.journal_id.returned_check_debit_account_id.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': rec.amount,
                                 'credit': 0}

                self.check_followup_post(create_move)

            if rec.payment_id.partner_type == 'supplier':
                move_line_id1 = {'account_id': rec.journal_id.default_account_id.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': rec.amount,
                                 'credit': 0}

                move_line_id2 = {'account_id': rec.journal_id.returned_check_credit_account_id.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': 0,
                                 'credit': rec.amount}

            create_move.line_ids = [(0, 0, move_line_id1), (0, 0, move_line_id2)]

            rec.state = 'returned'
            rec.check_followup_post(create_move)
            rec.message_post(body=_("Journal Entry created <strong>  %s </strong>") % create_move.name)

    def returned_2_close(self):
        # make journal Entry to  and change state to closed
        for rec in self:
            create_move = self.env['account.move'].create({'name': "Closed check For  " + rec.payment_id.name,
                                                           'journal_id': self.journal_id.id,
                                                           'date': rec.payment_id.date,
                                                           'check_followup_id': rec.id})

            move_line_id1 = False
            move_line_id2 = False
            if rec.payment_id.partner_type == 'customer':
                move_line_id1 = {'account_id': rec.payment_id.company_id.account_receivable.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': rec.amount,
                                 'credit': 0}

                move_line_id2 = {'account_id': rec.journal_id.returned_check_debit_account_id.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': 0,
                                 'credit': rec.amount}
                self.check_followup_post(create_move)

            if rec.payment_id.partner_type == 'supplier':
                move_line_id1 = {'account_id': rec.payment_id.company_id.account_payable.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': 0,
                                 'credit': rec.amount}

                move_line_id2 = {'account_id': rec.journal_id.returned_check_credit_account_id.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': rec.amount,
                                 'credit': 0}

            create_move.line_ids = [(0, 0, move_line_id1), (0, 0, move_line_id2)]
            rec.state = 'closed'
            rec.check_followup_post(create_move)
            rec.message_post(body=_("Journal Entry created <strong>  %s </strong>") % create_move.name)

    def under_collection_outstanding(self):
        # make journal Entry to reverse returned checks and change state to undercollectoin or outstanding
        for rec in self:

            create_move = self.env['account.move'].create({'name': "Reversed check " + rec.payment_id.name,
                                                           'journal_id': self.journal_id.id,
                                                           'date': rec.payment_id.date,
                                                           'check_followup_id': rec.id})

            move_line_id1 = False
            move_line_id2 = False
            if rec.payment_id.partner_type == 'customer':
                move_line_id1 = {'account_id': rec.journal_id.check_undercollection_account_id.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': rec.amount,
                                 'credit': 0}

                move_line_id2 = {'account_id': rec.journal_id.returned_check_debit_account_id.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': 0,
                                 'credit': rec.amount}
                self.check_followup_post(create_move)

                rec.state = 'under-collection'

            if rec.payment_id.partner_type == 'supplier':
                move_line_id1 = {'account_id': rec.journal_id.check_outstanding_account_id.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': 0,
                                 'credit': rec.amount}

                move_line_id2 = {'account_id': rec.journal_id.returned_check_credit_account_id.id,
                                 'move_id': create_move.id,
                                 'date': rec.payment_id.date,
                                 'debit': rec.amount,
                                 'credit': 0}

                rec.state = 'outstanding'

            create_move.line_ids = [(0, 0, move_line_id1), (0, 0, move_line_id2)]
            rec.check_followup_post(create_move)
            rec.message_post(body=_("Journal Entry created <strong>  %s </strong>") % create_move.name)

    def withdrawn_close(self):
        self.withdrawn()
        self.close()


class AccountJournal(models.Model):
    _inherit = "account.journal"

    check_undercollection_account_id = fields.Many2one('account.account', 'Check Under-Collection Account')
    check_outstanding_account_id = fields.Many2one('account.account', 'Check Outstanding Account')
    returned_check_debit_account_id = fields.Many2one('account.account', 'Returned Check Debit Account')
    returned_check_credit_account_id = fields.Many2one('account.account', 'Returned Check Credit Account')


class AccountPayment(models.Model):
    _inherit = "account.payment"

    check_type = fields.Selection([('direct', 'Due'), ('indirect', 'PDC')], string="Check Type",
                                  default='direct')
    date_due = fields.Date('Due Date')

    # TODO: make the constrains on the date_due so it must be
    # more than today and less than payment date + check grace period
    @api.constrains("date_due")
    def validiate_date_due_field(self):

        more_than = date.today()
        # TODO: The result is string type convert it to date type before comparing
        # less_than = fields.Date.to_string(self.date + relativedelta(days= self.company_id.check_grace_period * (365/12)  )) # BY moths
        less_than_string_type = fields.Date.to_string(
            self.date + relativedelta(days=self.company_id.check_grace_period))  # BY days
        less_than_date_type = fields.Date.to_date(less_than_string_type)  # The result is Date type

        if self.check_type == "indirect":
            if (self.date_due < more_than):
                raise ValidationError("Due Date must be more than today")
            if (self.date_due > less_than_date_type):
                raise ValidationError("Due Date must be less than payment date + check grace period")
            else:
                pass

    def _get_counterpart_move_line_vals(self, invoice=False):
        """
            in case of indirect check use default Receivalbe or Payable account rather than partner Account 
        """
        res = super(AccountPayment, self)._get_counterpart_move_line_vals(invoice)
        if self.check_type == 'indirect':
            account_id = False
            if self.partner_type == 'customer':
                account_id = self.company_id.account_receivable
                if not account_id:
                    raise UserError(_('Please enter Receivalbe account in settings'))
            if self.partner_type == 'supplier':
                account_id = self.company_id.account_payable
                if not account_id:
                    raise UserError(_('Please enter Payable account in settings'))
            res['account_id'] = account_id.id
        return res

    def _get_liquidity_move_line_vals(self, amount):
        """
            Update account value incase of indirect check
        """
        res = super(AccountPayment, self)._get_liquidity_move_line_vals(amount)
        if self.check_type == 'indirect':
            account_id = False
            if self.partner_type == 'customer':
                account_id = self.journal_id.check_undercollection_account_id
                if not self.journal_id.check_undercollection_account_id:
                    raise UserError(_("Please Enter under-collection account in your Journal"))
            if self.partner_type == 'supplier':
                account_id = self.journal_id.check_outstanding_account_id
                if not self.journal_id.check_outstanding_account_id:
                    raise UserError(_("Please Enter outstanding account in your Journal"))
            res['account_id'] = account_id.id
        return res

    # @api.multi
    '''def post(self):
        """
            Create Check Flowup record in case of indirect check and schedule activity 
        """
        rec = super(AccountPayment, self).post()
        if rec and self.check_type == 'indirect' and self.payment_method_code == 'check_printing':
            state = self.payment_type == 'outbound' and 'outstanding' or 'under-collection'
            create_folloup = self.env['account.checks.followup'].sudo().create({'payment_id': self.id, 'state': state})
            activity = self.env['mail.activity'].sudo().create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                # 'summary': summary,
                'date_deadline': self.date_due,
                'user_id': self.env.user.id,
                'res_id': create_folloup.id,
                'res_model_id': self.env['ir.model'].search([('model', '=', 'account.checks.followup')], limit=1).id,
            })
        return rec'''

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        
        for rec in self:
            method_code = rec.payment_method_line_id.code
            
            if rec.check_type == 'indirect':
                state = 'outstanding' if rec.payment_type == 'outbound' else 'under-collection'
                
                # Create Followup record
                followup = self.env['account.checks.followup'].sudo().create({
                    'payment_id': rec.id, 
                    'state': state
                })
                
                self.env['mail.activity'].sudo().create({
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'date_deadline': rec.date_due,
                    'user_id': self.env.user.id,
                    'res_id': followup.id,
                    'res_model_id': self.env['ir.model']._get_id('account.checks.followup'),
                })
                
        return res


class AccountMove(models.Model):
    _inherit = "account.move"

    check_followup_id = fields.Many2one('account.checks.followup', 'Check Followup')
