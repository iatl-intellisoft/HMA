# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL International Pvt. Ltd.
#    Copyright (C) 2018-TODAY Tech-Receptives(<http://www.iatl-sd.com>).
#
###############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CustodyClearance(models.Model):
    _name = 'custody.clearance'
    _rec_name = 'sequence'
    _description = 'Payment Clearance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sequence = fields.Char(readonly=True, string='Name')
    request_id = fields.Many2one('payment.request', string='Payment', tracking=True, required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=False, tracking=True,
                                  related='request_id.employee_id', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)####
    # department_id = fields.Many2one('hr.department', string='Department',
    #                                 tracking=True, readonly=True)
    partner_id = fields.Many2one('res.partner', related='request_id.partner_id', string="Partner",
                                 tracking=True,default=lambda self: self.env.user.partner_id.id)
    custody_amount = fields.Float(string="Custody Amount", related='request_id.amount')

    total_amount = fields.Float(
        'Total Amount', tracking=True, compute='_amount_all')
    total_clearance = fields.Float(string='Total Clearance', compute='_compute_total_clearance')

    is_renewable = fields.Boolean(string='Is Renewable', tracking=True, related='request_id.is_renewable',
                                  readonly=True)
    date = fields.Date(string='Date', default=fields.Date.context_today)
    payment_ids = fields.One2many(
        'account.payment', 'custody_clearance_id', string='payment', )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'), 
        ('approve', 'Approved'),
        ('wait_payment', 'Waiting Payment'),
        ('done', 'Done'),
        ('refuse', 'refused'),
    ], string='State', readonly=True, default='draft', tracking=True)

    account_id = fields.Many2one('account.account', string='Account', related='request_id.account_id',
                                 tracking=True,
                                 readonly=False)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company)
    journal_id = fields.Many2one('account.journal', string='Clearance Journal',
                                 tracking=True, default=lambda self: self.env.company.clearance_journal)
    creator = fields.Many2one('hr.employee', string='Creator', required=False,default=lambda self: self.env.user.employee_id.id)

    # related = 'company_id.clearance_journal'
# journal_id = fields.Many2one('account.journal', string='Clearance Journal',
#                                  tracking=True, default=lambda self: self.company_id.clearance_journal)

    # j2 = fields.Many2one('account.journal', string='Clearance Journal',
    #                      related='company_id.clearance_journal')
    payment_amount = fields.Float(related='total_amount', string="Payment Amount",
                                  tracking=True)
    request_remaining_amount = fields.Float( string="Remaining Amount",compute="copmute_request_remaining_amount",store=True) 
    move_id = fields.Many2one(
        'account.move', string='Move', tracking=True)

    custody_line_ids = fields.One2many('custody.clearance.line', 'clearance_id', string='Clearance Details',
                                       tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', string='ADD Documents', 
                                      help="You can select multiple document to upload.")
    move_created = fields.Boolean(string='move created', default=True)
    currency_id = fields.Many2one('res.currency', string="Currency", compute="set_currency_request", required=True, )

 
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        store=True,
        string="Truck",
        required=True,
    )

    driver_id = fields.Many2one(
        'res.partner',
        related="vehicle_id.driver_id",
        store=True,
        string="Driver"
    )

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.driver_id = self.vehicle_id.driver_id

    @api.depends('request_id')
    def copmute_request_remaining_amount(self):
        for rec in self:
            rec.request_remaining_amount = rec.request_id.remaining_amount

    @api.depends('request_id')
    def set_currency_request(self):
        for rec in self:            
            currency_id = self.env.user.company_id.currency_id.id
            if rec.request_id:
                currency_id = rec.request_id.currency_id.id
            rec.currency_id = currency_id 



    # @api.model_create_multi
    # def create(self, vals):
    #     seq = self.env['ir.sequence'].next_by_code('clearance.sequence') or '/'
    #     vals['sequence'] = seq
    #     return super(CustodyClearance, self).create(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            seq = self.env['ir.sequence'].next_by_code('clearance.sequence') or '/'
            vals['sequence'] = seq
        return super(CustodyClearance, self).create(vals_list)

 

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_submit(self):        
        if  self.request_id.remaining_amount < self.total_amount:
            raise ValidationError("عذرا لا يمكن أن تكون التصفية أكبر من مبلغ العهدة")
        if not self.custody_line_ids:
            raise ValidationError('Please enter clearance details first!')
         
       
        self.write({'state': 'approve'})
        
        self.request_id.remaining_amount = self.request_id.remaining_amount - self.total_amount  
        self.request_remaining_amount = self.request_id.remaining_amount 
        if  self.request_id.remaining_amount == 0:
            self.request_id.state = 'close'

             

    # def action_confirm(self):
    #     self.write({'state': 'confirm'})

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise ValidationError(
                    'Can not delete record state not in draft')
        return super(CustodyClearance, self).unlink()

    def action_approve(self):
        self.write({'state': 'approve'})

    def first_move_line(self, move):
        date = fields.Date.today()
        if not self.account_id:
            raise ValidationError(_('Entered payment request account'))
        # if self.currency_id == self.company_id.currency_id:
        move_line_ids = ({
            'partner_id': self.partner_id.id,
            'account_id': self.account_id.id,
            'currency_id': self.request_id.currency_id.id,
            'debit': 0.0,
            'credit': self.total_amount,
            'move_id': move.id, })
        # else:
        #     balance = self.currency_id._convert(self.total_amount, self.company_id.currency_id, self.company_id, date)
        #     move_line_ids = ({
        #         'partner_id': self.partner_id.id,
        #         'account_id': self.account_id.id,
        #         'currency_id': self.request_id.currency_id.id,
        #         'amount_currency': - self.total_amount,
        #         'debit': 0.0,
        #         'credit': balance,
        #         'move_id': move.id, })

        return move_line_ids

    def create_clearance_move_line(self, move):
        date = fields.Date.today()
        for line in self.custody_line_ids:
            # if self.currency_id == self.company_id.currency_id:
            vals = {
                'partner_id': line.partner_id.id,
                'account_id': line.account_id.id,
                'currency_id': self.request_id.currency_id.id,
                'debit': line.amount,
                'credit': 0.0,
                'move_id': move.id,
            }

            if line.analytic_account_id:
                vals['analytic_distribution'] = {
                    str(line.analytic_account_id.id): 100
                }
            # else:
            #     balance = self.currency_id._convert(line.amount, self.company_id.currency_id, self.company_id, date)
            #     vals = {'account_id': line.account_id.id,
            #             'currency_id': self.request_id.currency_id.id,
            #             'amount_currency': line.amount,
                       
            #             # 'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)] if line.analytic_tag_ids else False,

            #             'debit': balance,
            #             'credit': 0.0,
            #             'move_id': move.id,}
            #     if line.analytic_account_id:
            #         vals['analytic_distribution'] = {
            #             str(line.analytic_account_id.id): 100
            #         }
                    
            self.env['account.move.line'].with_context(
                check_move_validity=False).create(vals)

    def action_create_journal(self):
        if not self.move_id:
            move = self.env['account.move']
            move_line = self.env['account.move.line']
            move_id = move.create({
                'journal_id': self.journal_id.id,
                'ref': self.sequence,
                'payment_request_id': self.request_id.id,
                'currency_id': self.request_id.currency_id.id,
                'company_id': self.company_id.id, })

            move_line.with_context(
                check_move_validity=False).create(self.first_move_line(move_id))

            self.create_clearance_move_line(move_id)
            move_id.action_post()
            custody_payment = self.request_id.payment_ids[0]
            payment_line = custody_payment.move_id.line_ids.filtered(
                lambda r: r.account_id == self.account_id)
            clearance_line = move_id.line_ids.filtered(
                lambda r: r.account_id == self.account_id)
            lines_to_reconcile = (payment_line + clearance_line)
            lines_to_reconcile.reconcile()
            self.write({'move_id': move_id.id, 'move_created': False})

            if not self.is_renewable:
                if self.payment_amount == 0.0:
                    self.write({'state': 'done'})
                    self.request_id.write({'state': 'close'})
            else:
                if self.payment_amount == 0.0:
                    self.write({'state': 'done'})
                    self.request_id.write({'state': 'approve'})
        # else:
        #     raise ValidationError(_("The payment cann!"))

    def action_wait(self):
        self.write({'state': 'wait_payment'})

    def action_refuse(self):
        self.write({'state': 'refuse'})

    def action_done(self):
        if self.is_renewable:
            self.request_id.write({'state': 'approve'})
            self.write({'state': 'done'})
        elif not self.is_renewable:
            if self.payment_amount == 0.0:
                self.write({'state': 'done'})
            else:
                self.write({'state': 'approve'})

    @api.depends('custody_line_ids.amount')
    def _amount_all(self):
        """
        Compute the total amounts of custody.
        """
        for order in self:
            total = 0.0
            for line in order.custody_line_ids:
                total += line.amount
            order.update({
                'total_amount': total,
            })

    @api.depends('custody_line_ids')
    def _compute_total_clearance(self):
        for rec in self:
            rec.total_clearance = sum([line.amount for line in rec.custody_line_ids])

    # @api.onchange('employee_id')
    # def _onchange_employee_id(self):
    #     self.department_id = self.employee_id.department_id.id


class CustodyLines(models.Model):
    """
    Class that holds details of the clearance, which is mainly an expense account with some other relevant data.
    """
    _name = 'custody.clearance.line'
    _description = 'Custody Lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    account_id = fields.Many2one('account.account', string='Account', tracking=True,
                                 domain=[('internal_group', '=', 'expense')])
    partner_id = fields.Many2one('res.partner', string="Partner")
    amount = fields.Float(string="Amount", tracking=True, compute="_compute_total",)
    company_id = fields.Many2one('res.company',default=lambda self: self.env.company)
    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Cost Center', tracking=True)
    # analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags',
    #                                     domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    #                                     store=True, readonly=False,
    #                                     check_company=True, copy=True)
    clearance_type = fields.Selection([
        ('fuel', 'وقود للشاحنة'),
        ('gasoline', 'جاز للشاحنة'),
        ('violations', 'ايصالات و مخالفات'), 
    ], string='type',  default='fuel' )
    desc = fields.Text(string="Description", tracking=True)
     
    clearance_id = fields.Many2one(
        'custody.clearance', required=True, ondelete='cascade')
    
    quantity = fields.Float(
        string="Quantity",
        required=True
    )

    price_unit = fields.Float(
        string="Price",
        required=True
    )

 
    @api.depends('quantity', 'price_unit')
    def _compute_total(self):
        for rec in self:
            rec.amount = rec.quantity * rec.price_unit