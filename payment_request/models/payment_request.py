# -*- coding: utf-8 -*-

from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.fields import datetime
from odoo.osv import expression


class PaymentRequest(models.Model):
    _name = 'payment.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'
    _description = 'Payment Request'

    name = fields.Char(string="Reference", required=True, index=True, default='New', readonly=True)
    is_need_clearance = fields.Boolean(string="Need Clearance", )
    employee_id = fields.Many2one('hr.employee', string='Employee', required=False,
                                  default=lambda self: self.env.user.employee_id.id)
    creator = fields.Many2one('hr.employee', string='Creator', required=False,
                              default=lambda self: self.env.user.employee_id.id)
    department_id = fields.Many2one('hr.department', string='Department',
                                    default=lambda self: self.env.user.employee_id.department_id.id)
    partner_id = fields.Many2one('res.partner', string="Partner", required=False, tracking=True,
                                 default=lambda self: self.env.user.partner_id.id)  ###
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    clearance_days = fields.Integer(string="Clearance Days", required=False, default='30')
    date_clearance = fields.Date(string='Date Clearance', compute='_compute_clearance_date')
    account_id = fields.Many2one('account.account', string='Account',related='company_id.custody_account_id',store=True,tracking=True, readonly=False) 
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=False, )
    company_id = fields.Many2one('res.company', string='Company', store=True, readonly=False, tracking=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string="Currency", required=True,
                                  default=lambda self: self.env.company.currency_id)
    balance = fields.Float(
        'Balance', tracking=True, compute='_balance_compute', store=True )
    is_purchase = fields.Boolean(string="Is Purchase", readonly=True)
    invoice_id = fields.Many2one("account.move", string="Invoice", required=False, )
    amount = fields.Float('Amount', tracking=True)
    base_amount = fields.Float('base amount')
    line_ids = fields.One2many("payment.request.line", "payment_id", string="Payment Line", required=False, )
    move_id = fields.Many2one("account.move", string="Bill", required=False, )
    move_line_ids = fields.Many2many('account.move.line', compute='_get_entries', readonly=True)
    clearance_ids = fields.One2many('custody.clearance', 'request_id')
    is_renewable = fields.Boolean(string='Is Renewable', tracking=True ,default="1")
    payment_ids = fields.One2many(
        'account.payment', 'payment_request_id', string='payment', )
    note = fields.Char(string='Note')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submit'), 
        ('wait_payment', 'Waiting approve & Payment'),
        ('paid', 'Paid'),
        ('close', 'Closed'),
        ('cancel', 'Cancel'),
    ], string='State', readonly=True, default='draft', tracking=True)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     tracking=5)
    total_amount = fields.Float('Total Amount ', store=True , required=True)
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    on_time = fields.Boolean(string='On Time', compute='_compute_on_time')
    can_reset_to_draft = fields.Boolean(compute='_compute_can_reset_to_draft')

    niration = fields.Char(string='Niration')
    total_amount = fields.Float('Total Amount ', store=True , required=True)
   

    remaining_amount = fields.Float(
    string="Remaining", 
    store=True,
    compute="_onchange_employee_id"
    )


    req_amount = fields.Float('Required Amount ', store=True)
    maintenance_id = fields.Many2one(
        'maintenance.request',
        string="Maintenance Request",
        domain="[('stage_id.name','=','طلب جديد')]",
        store=True,
    )

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        store=True,
        string="Truck"
    )

    driver_id = fields.Many2one(
        'res.partner',
        related="vehicle_id.driver_id",
        store=True,
        string="Driver"
    )

    custody_type = fields.Selection([
        ('maintenance', 'الصيانة الدورية'),
        ('car_wash', 'مغسلة'),
        ('car_tire_repair', 'بنشر'),
        ('violations','مخالفات حكومية'),
        ('insurance', 'تأمين'),
        ('monthly_inspection', 'تفتيش شهري'),
        ('other', 'أخرى'),
    ], string='Type', store=True)
    is_negative_remaining_amount = fields.Boolean(store=True)
    negative_remaining_amount= fields.Integer(store=True)

    @api.onchange('remaining_amount')     
    def _is_negative_remaining_amount(self):
        if self.remaining_amount and self.remaining_amount < 0:
            self.negative_remaining_amount = self.remaining_amount
            self.is_negative_remaining_amount = True
    

  
    @api.onchange('maintenance_id')
    def _onchange_maintenance(self):
        if self.custody_type == 'maintenance' and self.maintenance_id:
            self.vehicle_id = self.maintenance_id.vehicle_id
            self.driver_id = self.maintenance_id.vehicle_id.driver_id
            self.req_amount = self.maintenance_id.maintenance_cost

  
    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.custody_type == 'fuel' and self.vehicle_id:
            self.driver_id = self.vehicle_id.driver_id


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('payment.request') or _('New')
        return super(PaymentRequest, self).create(vals_list)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """
        Override name search in order to make custody requests searchable using employee name.
        :return: Financial custody filtered objects
        """
        if operator == 'ilike' and not (name or '').strip():
            pass
        elif operator in ('ilike', 'like', '=', '=like', '=ilike'):
            domain = expression.AND([
                args or [],
                ['|', ('name', operator, name), ('partner_id.name', operator, name)]
            ])
            payment_ids = self._search(domain, limit=limit, access_rights_uid=name_get_uid)
            return self.browse(payment_ids).name_get()
        return super(PaymentRequest, self)._name_search(name, args=args, operator=operator, limit=limit,
                                                        name_get_uid=name_get_uid)

    def name_get(self):
        res = []
        for payment in self:
            name = payment.name
            if payment.partner_id.name:
                name = '%s - %s - %s - %s' % (name, payment.partner_id.name, payment.date, payment.amount)
            res.append((payment.id, name))
        return res

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self.department_id = self.employee_id.department_id.id
        self.partner_id = self.employee_id.user_id.partner_id.id
        prev_custody = self.env['payment.request'].search([('employee_id','=',self.employee_id.id),('state','=','paid'),('is_need_clearance','=',True)],limit=1)
        if prev_custody:
            self.remaining_amount = prev_custody.remaining_amount

    @api.depends('line_ids.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.line_ids:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                # 'total_amount': amount_untaxed + amount_tax,
            })

    def call_link(self):
        day_now = datetime.date(datetime.today())
        RaymentRequest = self.env['payment.request'].search([])
        for payment in RaymentRequest:
            dead_line = payment.date
            dead_line += timedelta(days=payment.clearance_days)
            if (day_now - payment.date_clearance).days == 1 and payment.state != 'close':
                self.env['mail.message'].create({'email_from': self.env.user.partner_id.email,
                                                 'author_id': self.env.user.partner_id.id,
                                                 'model': 'mail.channel',
                                                 'subtype_id': self.env.ref('mail.mt_comment').id,
                                                 'body': "payment " + payment.name + " is late",
                                                 'channel_ids': [(4, self.env.ref(
                                                     'payment_request.channel_accountant_group').id)],
                                                 'res_id': self.env.ref(
                                                     'payment_request.channel_accountant_group').id,
                                                 })

    @api.depends('move_line_ids.debit', 'move_line_ids.credit')
    def _balance_compute(self):
        """
        Compute the total amounts of custody.
        """
        total = 0.0
        for move in self:
            for line in move.move_line_ids:
                if self.currency_id == self.company_id.currency_id:
                    total += line.debit - line.credit
                else:
                    total += line.amount_currency

        self.balance = total

    def _get_entries(self):
        self.move_line_ids = False
        AccountMoveLine = self.env['account.move.line']
        for rec in self:
            move_ids = self.env['account.move'].search([('payment_request_id', '=', rec.id), ('state', '=', 'posted')])
            if rec.is_need_clearance and rec.account_id and rec.partner_id:
                moves = AccountMoveLine.search([('move_id', 'in', move_ids.ids), ('account_id', '=', rec.account_id.id),
                                                ('partner_id', '=', rec.partner_id.id)])
                rec.move_line_ids = [(6, 0, [m.id for m in moves])] or False

    @api.depends('date', 'clearance_days')
    def _compute_clearance_date(self):
        for rec in self:
            rec.date_clearance = rec.date + timedelta(days=rec.clearance_days)

    def action_set_to_draft(self):
        if self.move_id:
            self.move_id.button_draft()
        self.write({'state': 'draft'})

    def action_submit(self): 
        prev_custody = self.env['payment.request'].search([('employee_id','=',self.employee_id.id),('state','=','paid'),('is_need_clearance','=',True)],limit=1)
        if prev_custody:
            self.remaining_amount = prev_custody.remaining_amount
            
        if self.remaining_amount < 0 :
            self.is_negative_remaining_amount = True
            self.negative_remaining_amount = self.remaining_amount
        self.write({'state': 'wait_payment'})
       

    def reset_to_draft(self):
        if self.move_id:
            self.move_id.button_draft()
        self.write({'state': 'draft'})
        self.payment_ids = False
        # self.write({'move_line_ids': [(5, 0, 0)]})
        # order.order_line.write({'move_dest_ids': [(5, 0, 0)]})

    def action_close(self):
        if self.balance == 0.0:
            self.write({'state': 'close'})
        else:
            view_id = self.env.ref('payment_request.view_account_payment_request_form').id
            return {'type': 'ir.actions.act_window',
                    'name': 'Register Custody Payment',
                    'res_model': 'account.payment',
                    'target': 'new',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': view_id,
                    'views': [(self.env.ref('payment_request.view_account_payment_request_form').id, 'form'), ],
                    'context': {'default_payment_request_id': [(4, self.id, None)], 'close': True}
                    }

    def action_cancel(self):
        if self.move_id:
            self.move_id.button_cancel()
        self.write({'state': 'cancel'})

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise ValidationError(
                    'Can not delete record state not in draft')
        return super(PaymentRequest, self).unlink()

    def _compute_on_time(self):
        day_now = datetime.date(datetime.today())
        self.on_time = False
        # send_notification
        for payment in self:
            if payment.date:
                dead_line = payment.date
                dead_line += timedelta(payment.clearance_days)
                if (day_now - dead_line).days >= 1 and payment.state != 'close' and payment.is_need_clearance == True:
                    payment.on_time = False
                else:
                    payment.on_time = True

    def _compute_can_reset_to_draft(self):
        for payment_request in self:
            can_reset_to_draft = True
            for payment in payment_request.payment_ids:
                if payment.state != 'draft':
                    can_reset_to_draft = False
            payment_request.can_reset_to_draft = can_reset_to_draft


class PaymentRequestLine(models.Model):
    _name = 'payment.request.line'
    _description = 'Payment Request Line'

    payment_id = fields.Many2one("payment.request", string="Payment", required=False, )
    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Char(string='Label' )
    currency_id = fields.Many2one('res.currency', string="Currency", 
                                  related='payment_id.currency_id')
    
    total_amount = fields.Float('Total Amount ', related='payment_id.total_amount')
    niration = fields.Char(string='Niration' , related='payment_id.niration')
    quantity = fields.Float(string='Quantity',
                            default=1.0, digits='Product Unit of Measure',
                            help="The optional quantity expressed by this line, eg: number of product sold. "
                                 "The quantity is not a legal requirement but is very useful for some reports.")
    price_unit = fields.Float(string='Unit Price', digits='Product Price', currency_field='currency_id')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure',
                                     domain="[('category_id', '=', product_uom_category_id)]")
    partner_id = fields.Many2one('res.partner', string="Partner",
                                 related='payment_id.partner_id')
    expense_account_id = fields.Many2one('account.account', string='Account', readonly=False, )
    tax_ids = fields.Many2many('account.tax', string='Taxes', help="Taxes that apply on the base amount",
                               check_company=True, domain=['|', ('active', '=', False), ('active', '=', True)])

    # analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags',
    #                                     domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    #                                     store=True, readonly=False,
    #                                     check_company=True, copy=True)
    price_subtotal = fields.Monetary(string='Subtotal', store=True, readonly=True, compute='_compute_amount',
                                     currency_field='currency_id')
    company_id = fields.Many2one(related='payment_id.company_id', store=True, readonly=True,
                                 default=lambda self: self.env.company)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')

    price_tax = fields.Float(compute='_compute_amount', string='Total Tax', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)

    @api.depends('quantity', 'price_unit', 'tax_ids')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit
            # self.currency_id._convert(line.price_unit, line.payment_id.currency_id, line.company_id,
            #                               line.payment_id.date or fields.Date.today(), round=False)
            taxes = line.tax_ids.compute_all(price, line.payment_id.currency_id, line.quantity,
                                             product=line.product_id, partner=line.partner_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
                    'account.group_account_manager'):
                line.tax_ids.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_ids.id])

    @api.depends('product_id', 'quantity', 'price_unit')
    def _compute_subtotal(self):
        for rec in self:
            rec.price_subtotal = rec.quantity * rec.price_unit

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = {}
        if not self.product_id:
            return result

        self.product_uom_id = self.product_id.uom_po_id or self.product_id.uom_id
        result['domain'] = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}

        product_lang = self.product_id.with_context(
            lang=self.partner_id.lang,
            partner_id=self.partner_id.id,
        )
        self.name = product_lang.display_name
        if product_lang.description_purchase:
            self.name += '\n' + product_lang.description_purchase

        if self.product_id:
            self.price_unit = self.product_id.standard_price
            self.expense_account_id = self.product_id.property_account_expense_id.id or self.product_id.categ_id.property_account_expense_categ_id.id
        return result
class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string="Truck"
    )
    maintenance_cost = fields.Float(
        string="Maintenance Cost"
    )
