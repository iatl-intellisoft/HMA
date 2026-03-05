from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.translate import html_translate


class HrLoan(models.Model):
    """"""
    _name = 'hr.loan'
    _inherit = ['mail.thread']
    _description = "HR Loan Request"

    @api.depends('loan_line_ids', 'loan_line_ids.paid', 'loan_amount')
    def _compute_amount(self):
        """
        A method to compute total loan amount
        """
        for loan in self:
            total_paid_amount = 0.00
            for line in loan.loan_line_ids:
                if line.paid == True:
                    total_paid_amount += line.paid_amount

            balance_amount = loan.loan_amount - total_paid_amount
            loan.total_amount = loan.loan_amount
            loan.balance_amount = balance_amount
            loan.total_paid_amount = total_paid_amount
            loan.change_state()

    def _get_old_loan(self):
        """
        A method to get old employee loan if exist
        """
        old_amount = 0.00
        for loan in self.search([('employee_id', '=', self.employee_id.id)]):
            if loan.id != self.id:
                old_amount += loan.balance_amount
        self.loan_old_amount = old_amount

    name = fields.Char(string="Loan Name", default="/", readonly=True)
    date = fields.Date(string="Date Request", default=fields.Date.today(), readonly=True, required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, store=True)
    parent_id = fields.Many2one('hr.employee', related="employee_id.parent_id", string="Manager")
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True,
                                    string="Department", store=True)
    job_id = fields.Many2one('hr.job', related="employee_id.job_id", readonly=True, string="Job Position")
    emp_salary = fields.Float(string="Employee Salary", compute='_compute_employee_salary', readonly=True)
    max_loan = fields.Float(string="Max Loan", readonly=True, index=True)
    loan_old_amount = fields.Float(string="Old Loan Not Paid", compute='_get_old_loan')
    emp_account_id = fields.Many2one(related="loan_type.emp_account_id", string="Employee account")
    # voucher_id = fields.Many2one('account.voucher', 'Voucher')
    move_id = fields.Many2one('account.move', 'Receipt')

    treasury_account_id = fields.Many2one(related="loan_type.treasury_account_id", string="Treasury Account")
    journal_id = fields.Many2one(related="loan_type.journal_id", string="Journal")
    loan_amount = fields.Float(string="Loan Amount", required=True, store=True)
    total_amount = fields.Float(string="Total Amount", readonly=True, compute='_compute_amount', store=True)
    balance_amount = fields.Float(string="Balance Amount", compute='_compute_amount', store=True)
    total_paid_amount = fields.Float(string="Total Paid Amount", compute='_compute_amount', store=True)
    no_month = fields.Integer(string="No Of Month", default=1)
    payment_start_date = fields.Date(string="Start Date of Payment", required=True, default=fields.Date.today())
    payment_end_date = fields.Date(string='end date of payment', compute='_get_end_date')
    loan_line_ids = fields.One2many('hr.loan.line', 'loan_id', string="Loan Line", index=True)
    loan_type = fields.Many2one('loan.type', string="Loan Type", index=True, required=True, ondelete='restrict')
    total_loan = fields.Float(string="Total Loan", compute='_compute_total_loan', store=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('hr_manager', 'Waiting HR Manager Approval'),
        ('wait_finance', 'Waiting Finance Approval'),
        ('wait_gm', 'Waiting General Manager Approval'),
        ('approve', 'Approved'),
        ('close', 'Close'),
        ('refuse', 'Refused'),
        ('cancel', 'Cancel'),
    ], string="State", default='draft', track_visibility='onchange', copy=False, )

    loan_request_website_description = fields.Html('Body Template', sanitize_attributes=False,
                                                   translate=html_translate,
                                                   compute="get_loan_request_website_description")
    loan_request_template_id = fields.Many2one('mail.template', string='Loan Request Template',
                                               related='company_id.loan_request_template_id')

    salary_advance_website_description = fields.Html('Body Template', sanitize_attributes=False,
                                                     translate=html_translate,
                                                     compute="get_salary_advance_website_description")
    salary_advance_template_id = fields.Many2one('mail.template', string='Salary Advance Template',
                                                 related='company_id.salary_advance_template_id')
    need_reason = fields.Boolean(related="loan_type.need_reason")
    reason = fields.Text(string="Reason")

    @api.model
    def create(self, vals):
        """
        A create method was inherited to create loan.
        """
        vals['name'] = self.env['ir.sequence'].get('hr.loan.req') or ' '
        vals['max_loan'] = self.emp_salary * 50 / 100
        res = super(HrLoan, self).create(vals)

        return res

    @api.depends('payment_start_date', 'no_month')
    def _get_end_date(self):
        """
        A method to compute loan end date by using loan start date and number of months
        """
        for rec in self:
            if rec.payment_start_date and rec.no_month:
                rec.payment_end_date = rec.payment_start_date + relativedelta(months=+rec.no_month)

    @api.constrains('total_loan', 'loan_line_ids.paid_amount')
    def _check_total_loan(self):
        """
        A method to check paid loan... total paid loan must be less than or equal loan amount.
        """
        for rec in self:
            if rec.total_loan > rec.total_amount:
                raise ValidationError(_("Total Installments can't be Bigger than Loan Amount!"))

    @api.constrains('date', 'employee_id')
    def _check_employee_trial_end(self):
        """
        A method to ensure that the employee deserves the loan or not.
        """
        for rec in self:
            if rec.employee_id.contract_id.trial_date_end:
                if rec.date < rec.employee_id.contract_id.trial_date_end:
                    raise ValidationError(_("Employee in trial period is not allowed To request loans!"))

    @api.constrains('no_month')
    def _check_no_month(self):
        """
        A method to ensure the number of months are greeter than zero.
        """
        for rec in self:
            if rec.no_month <= 0:
                raise ValidationError(_("The number of monthes must be more than zero!"))

    @api.constrains('loan_amount')
    def _check_loan_amount(self):
        """
        A method to ensure the loan amount are less than maximum loan amount.
        """
        for order in self:
            if order.loan_type.max_loan_amount:
                max_amount = order.loan_type.max_loan_amount.compute_rule_amount(order.employee_id)

                if order.loan_amount > max_amount:
                    raise ValidationError(_("Loan amount must not be greater allowed Max amount !"))

    @api.depends('employee_id.contract_id.wage')
    def _compute_employee_salary(self):
        """
        A method to compute employee salary.
        """
        for rec in self:
            rec.emp_salary = rec.employee_id.contract_id.wage

    @api.depends('loan_line_ids.paid_amount')
    def _compute_total_loan(self):
        """
        A method to compute total paid loan amount.
        """
        total = 0.0
        # if self.ids:
        for rec in self:
            if rec.loan_line_ids:
                self._cr.execute("select sum(paid_amount)as total from hr_loan_line where loan_id = %s ", (rec.id,))
                total = self._cr.fetchall()[0][0]
            rec.total_loan = total

    @api.constrains('employee_id')
    def _check_employee_id(self):
        """
        A method to check employee have old unpaid loan or not.
        """
        for rec in self:
            if rec.employee_id and rec.loan_type.no_unpaid:
                unpaid_loans = self.env['hr.loan.line'].search(
                    [('employee_id', '=', rec.employee_id.id), ('paid', '=', False), ('loan_id', '!=', rec.id)])
                if unpaid_loans:
                    raise ValidationError(_('Not allow old installment unpaid.'))

    @api.depends('loan_request_template_id', 'loan_request_template_id.body_html')
    def get_loan_request_website_description(self):
        """
        A method to create loan request website description template
        """
        for rec in self:
            rec.loan_request_website_description += rec.loan_request_website_description
            if rec.loan_request_template_id and rec.id:
                fields = ['body_html']
                template_values = rec.loan_request_template_id.generate_email([rec.id], fields=fields)
                rec.loan_request_website_description = template_values[rec.id].get('body_html')

    @api.depends('salary_advance_template_id', 'salary_advance_template_id.body_html')
    def get_salary_advance_website_description(self):
        """
        A method to create advance salary loan website description template
        """
        for rec in self:
            rec.salary_advance_website_description += rec.salary_advance_website_description
            if rec.salary_advance_template_id and rec.id:
                fields = ['body_html']
                template_values = rec.salary_advance_template_id.generate_email([rec.id], fields=fields)
                rec.salary_advance_website_description = template_values[rec.id].get('body_html')

    def action_refuse(self):
        """
        A method to refuse loan request before start payment.
        """
        for rec in self:
            if rec.total_paid_amount > 0:
                raise ValidationError(_("you can't refuse loan request after installement payment started"))
            elif rec.move_id:
                if rec.move_id.state == 'draft':
                    rec.state = 'refuse'
                    rec.move_id.unlink()
                elif rec.move_id.state == 'cancel':
                    rec.state = 'refuse'
                else:
                    raise ValidationError(
                        _("There Is An A voucher In State %s You Shoud Cancel It Or Delet It First!") % (
                            rec.move_id.state))
            else:
                rec.state = 'refuse'

    @api.model
    def _get_max_loan(self):
        """
        A method to get max advance salary loan amount using employee salary.
        """
        emp_salary = self.emp_salary
        max_loan = emp_salary * 50 / 100
        self.max_loan = max_loan

    def action_set_to_draft(self):
        """
        A method to set loan request draft before start payment.
        """
        for rec in self:
            if rec.total_paid_amount > 0:
                raise ValidationError(
                    _("you can't return loan request to draft state after installement payment started"))
            rec.state = 'draft'

    def onchange_employee_id(self, employee_id=False):
        """
        A method to compute loan when employee was change.
        """
        old_amount = 0.00
        if employee_id:
            for loan in self.search([('employee_id', '=', employee_id)]):
                if loan.id != self.id:
                    old_amount += loan.balance_amount
            return {
                'value': {
                    'loan_old_amount': old_amount}
            }

    @api.onchange('loan_type')
    def onchange_loan_type(self):
        """
        A method to change loan configuration when loan type was change.
        """
        self._get_max_loan()
        self.treasury_account_id = self.loan_type.treasury_account_id.id
        self.emp_account_id = self.loan_type.emp_account_id.id
        self.journal_id = self.loan_type.journal_id.id
        self.no_month = self.loan_type.no_month
        emp_salary = self.emp_salary
        # max_loan = emp_salary * 50 / 100
        self.loan_amount = self.loan_type.amount
        if self.loan_type.installment_type == 'depends_on_payroll':
            self.loan_amount = (emp_salary * self.loan_type.percentage) / 100

    @api.onchange('employee_id')
    def onchange_employee(self):
        """
        A method to change loan type to none when loan employee was change.
        """
        self.loan_type = None

    def action_cancel(self):
        """
        A method to cancel loan request before start payment.
        """
        for rec in self:
            if rec.total_paid_amount > 0:
                raise ValidationError(_("you can't cancel loan request after installement payment started"))
            elif rec.move_id:
                if rec.move_id.state == 'draft':
                    rec.state = 'cancel'
                    rec.move_id.unlink()
                elif rec.move_id.state == 'cancel':
                    rec.state = 'cancel'
                else:
                    raise ValidationError(
                        _("There is an a receipt in state %s, You Should cancel it Or delete it first!") % (
                            rec.move_id.state))
            elif rec.loan_line_ids.filtered('payslip_id'):
                raise ValidationError(_("Sorry! you can't cancel this record; There is a payslip /s for this record!"))

            rec.state = 'cancel'

    def action_approve(self):
        """
        A method to approve loan request.
        """

        for loan in self:
            if not loan.emp_account_id or not loan.treasury_account_id:
                raise UserError(_(
                                 "You must enter employee account & Treasury account and journal to approve "))
            if not loan.loan_line_ids:
                raise UserError(_( 'You must compute Loan Request before Approved'))
            loan_name = loan.employee_id.name
            reference = loan.name
            journal_id = loan.journal_id.id
            emp_partner = loan.employee_id.work_contact_id    
            if not emp_partner:
                raise ValidationError(_('Please add Partner for this Employee.'))

            move_id = self.env['account.move'].sudo().create([
                {
                    'date': loan.date,
                    'partner_id': emp_partner.id,
                    'journal_id': journal_id,
                    'move_type': 'entry',

                    'line_ids': [
                        (0, 0, {
                            'name': loan_name,
                            'partner_id': emp_partner.id,
                            'account_id': loan.emp_account_id.id,
                            'price_unit': loan.loan_amount,
                            'debit': loan.loan_amount,
                            'date_maturity': False,
                        }
                         ),
                        (0, 0, {
                            'name': loan_name,
                            'partner_id': emp_partner.id,
                            'account_id': emp_partner.property_account_payable_id.id,
                            'price_unit': loan.loan_amount,
                            'credit': loan.loan_amount,
                            'date_maturity': loan.date or fields.Date.today(),
                        }
                         ),

                    ],
                }
            ])

            loan.write({'state': "approve", 'move_id': move_id.id})
            # self.write({'state': "approve"})
        return True

    def compute_loan_line(self):
        """
        A method to compute loan amount ber record using number of month.
        """
        dates = []
        diff = 0.0
        total = 0.0
        loan_line = self.env['hr.loan.line']
        loan_line.search([('loan_id', '=', self.id)]).unlink()
        for loan in self:
            date_start_str = datetime.strptime(str(loan.payment_start_date), '%Y-%m-%d')
            counter = 1
            amount_per_time = int(loan.loan_amount / loan.no_month)

            for i in range(1, loan.no_month + 1):
                line_id = loan_line.create({
                    'paid_date': date_start_str,
                    'paid_amount': amount_per_time,
                    'payment_date': date_start_str,
                    'employee_id': loan.employee_id.id,
                    'loan_id': loan.id})
                counter += 1
                date_start_str = date_start_str + relativedelta(months=self.loan_type.number_incerment)
            for line in loan.loan_line_ids:
                total = total + line.paid_amount
                diff = loan.total_amount - total
                if isinstance(line.paid_date, date):
                    dates.append(line.paid_date)
            date_m = max(dates)
            if date_m:
                line.write({'paid_amount': amount_per_time + diff})

        return True

    def action_confirm(self):
        """
        A method to confirm loan request.
        """
        self.write({
            'state': 'confirm'
        })
    def action_confirm_hr_manager(self):
        """
        A method to confirm loan request.
        """
        self.write({
            'state': 'wait_finance'
        })
    def action_confirm_finance_manager(self):
        """
        A method to confirm loan request.
        """
        self.write({
            'state': 'wait_gm'
        })

    def action_submit(self):
        """
        A method to submit loan request.
        """
        self.compute_loan_line()
        self.write({
            'state': 'wait_finance'
        })

    def button_reset_balance_total(self):
        """
        A method to refresh loan balance.
        """
        total_paid_amount = 0.00
        for loan in self:
            for line in loan.loan_line_ids:
                if line.paid == True:
                    total_paid_amount += line.paid_amount
            balance_amount = loan.loan_amount - total_paid_amount
            self.write({'total_paid_amount': total_paid_amount, 'balance_amount': balance_amount})

    def unlink(self):
        """
        A method to delete loan record.
        """
        for loan in self:
            if loan.state not in ('draft',):
                raise UserError(_('You can not delete record not in draft state.'))
        return super(HrLoan, self).unlink()

    def change_state(self):
        for rec in self:
            if rec.total_amount > 0:
                if rec.total_paid_amount == rec.total_amount:
                    rec.write({'state': 'close'})
                if rec.total_paid_amount != rec.total_amount and  rec.state == 'close':
                    rec.write({'state': 'approve'})


class HrLoanLine(models.Model):
    """"""
    _name = "hr.loan.line"
    _description = "HR Loan Request Line"
    _inherit = ['mail.thread']

    name = fields.Char(compute='_name_get')
    paid_date = fields.Date(string="Payment Date", required=True, track_visibility='onchange')
    employee_id = fields.Many2one('hr.employee', string="Employee")
    paid_amount = fields.Float(string="Paid Amount", required=True, track_visibility='always')
    paid = fields.Boolean(string="Paid", track_visibility='onchange')
    notes = fields.Text(string="Notes")
    loan_type = fields.Many2one('loan.type', related='loan_id.loan_type', store=True)
    loan_id = fields.Many2one('hr.loan', string="Loan Ref.", ondelete='restrict')
    payslip_id = fields.Many2one('hr.payslip', string="Payslip Ref.", track_visibility='onchange', copy=False,
                                 ondelete='set null')
    payment_date = fields.Date(string="Payment Date", required=False, )
    company_id = fields.Many2one('res.company', 'Company', required=False, default=lambda self: self.env.company)

    @api.depends('employee_id.name', 'loan_id.loan_type.name', 'paid_date')
    def _name_get(self):
        """
        A method to rename loan path after create.
        """
        for rec in self:
            if rec.employee_id.name and rec.loan_id.loan_type.name and str(rec.paid_date):
                rec.name = rec.employee_id.name + ' - ' + rec.loan_id.loan_type.name + ' - ' + str(rec.paid_date)
            else:
                rec.name = ' '

    def postpone_month(self):
        """
        A method to postpone payment to next month
        """
        paid_date_str = datetime.strptime(str(self.paid_date), '%Y-%m-%d')
        loan_lines = self.env['hr.loan.line'].search(
            [('loan_id', '=', self.loan_id.id), ('paid_date', '>=', self.paid_date)])
        for line in loan_lines:
            if line.paid:
                raise UserError(_("You can not postpone paid loan"))
            line.write({'paid_date': datetime.strptime(str(line.paid_date), '%Y-%m-%d') + relativedelta(months=1)})

    def action_paid_amount(self):
        """
        A method to set loan in paid state.
        """
        self.write({'paid': True})
        self.loan_id.change_state()
        return True


class Employee(models.Model):
    """"""
    _inherit = "hr.employee"

    loan_amount = fields.Float(string="loan Amount", compute='_compute_loans')
    loan_count = fields.Integer(string="Loan Count", compute='_compute_loans')
    loan_ids = fields.One2many('hr.loan.line', 'employee_id', string="Loan lines")
    loan_request_ids = fields.One2many('hr.loan', 'employee_id', string="Loan Request")

    def _compute_loans(self):
        """
        A method to compute loan remaining amount and number of loan request.
        """
        for rec in self:
            count = 0
            loan_remain_amount = 0.00
            # loan_ids = self.env['hr.loan'].search([('employee_id', '=', self.id)])
            for loan in rec.loan_request_ids:
                loan_remain_amount += loan.balance_amount
                count += 1
            rec.loan_count = count
            rec.loan_amount = loan_remain_amount


class LoanType(models.Model):
    """"""
    _name = 'loan.type'

    name = fields.Char("Name", required=True)
    treasury_account_id = fields.Many2one('account.account', string="Treasury Account")
    journal_id = fields.Many2one('account.journal', string="Journal",
                                 domain=[('type', '=', 'purchase')])
    loan_id = fields.One2many('hr.loan', 'loan_type', string="Loan")
    emp_account_id = fields.Many2one('account.account', string="Employee Account")
    no_month = fields.Integer(string="No Of Month", default=1, required=True)
    active = fields.Boolean("Active", default=True)
    installment_type = fields.Selection([('fixed', 'Fixed'),
                                         ('depends_on_payroll', 'Depends On Payroll ')]
                                        , 'Type', default='fixed', required=True)

    amount = fields.Float('Amount', )
    code = fields.Char(string='Code')
    rule_id = fields.Many2one('hr.salary.rule', string='Salary rule', required=True, domain=[('use_type', '=', 'loan')])
    percentage = fields.Float('Percentage')
    salary_advance = fields.Boolean("Salary Advance")
    max_loan_amount = fields.Many2one("hr.salary.rule", string="Max Loan Amount", required=False,
                                      help='The max loan amount requested must not be grate'
                                           ' that formula in this rule Ex: Employee 5 Basic')
    no_unpaid = fields.Boolean(string="Not allow old unpaid installment ")
    need_reason = fields.Boolean(string='Need Reason')
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)

    number_incerment = fields.Integer(string="Month Number Incerment",default=1)

    # _sql_constraints = [
    #     ('code_uniq', 'Check(1=1)', "The code of loan type must be unique")]

    @api.constrains('code')
    def _check_loan_code_unique(self):
        loan_code_count = self.env['loan.type'].search_count([
            ('code', '=', self.code), ('company_id', '=', self.env.company.id)])
        if loan_code_count > 1:
            raise ValidationError(_('The code of loan should be unique in company'))
