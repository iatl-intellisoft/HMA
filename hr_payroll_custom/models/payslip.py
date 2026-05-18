from collections import defaultdict, Counter
from functools import reduce

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError, ValidationError
#from odoo.addons.hr_payroll.models.browsable_object import BrowsableObject, InputLine, WorkedDays, Payslips
from datetime import datetime , date
import calendar

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT,DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.safe_eval import safe_eval
from dateutil import relativedelta
from datetime import datetime, time

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'


    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Verify'),
        ('paid', 'Paid'),
        ('close', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')

    def compute_payslip_run(self):
        '''
            this method will compute the batch payslips 
        '''
        if self.slip_ids:
            for rec in self.slip_ids:
                rec.sudo().compute_sheet()

    def draft_payslip_run(self):
        '''
            this will change the state of the batch payslips to draft 
        '''
        payslips = self.slip_ids.filtered(lambda slip: slip.state != 'done')
        for payslip in payslips:
            payslip.action_payslip_draft()

    def action_draft(self):
        res = super(HrPayslipRun, self).action_draft()
        for rec in self:
            rec.slip_ids.action_payslip_cancel()
            rec.slip_ids.action_payslip_draft()
        return res

    def action_payslip_run_cancel(self):
        
        ## Cancel Payslips
        for rec in self:
            rec.slip_ids.action_payslip_cancel()
        
        return self.write({'state': 'cancel'})


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'


    net_amount = fields.Float(string='Net Amount', compute='_compute_net_amount')
    bank_id = fields.Many2one('res.bank', readonly=False,store=True) #related='employee_id.bank_id',
    num_work_days = fields.Float(string="Work Days",compute="_compute_days")

    # @api.onchange('employee_id', 'struct_id', 'contract_id', 'date_from', 'date_to')
    # def _onchange_employee(self):
    #     """
    #     """
    #     super(HrPayslip, self)._onchange_employee()
    #     self.bank_id = False
    #     if self.employee_id:
    #         self.bank_id = self.employee_id.bank_id
            

    @api.depends('date_from', 'date_to')
    def _compute_days(self):
        # str_now = datetime.now().date()
        days = 0
        month_range = 1
        # self.num_work_days = 0
        for slip in self:
            worked_days = 0
            slip.num_work_days
            if slip.date_from and slip.date_to:
                date_from = datetime.strptime(str(slip.date_from), '%Y-%m-%d')
                date_to_days = datetime.strptime(str(slip.date_to), '%Y-%m-%d')
                month_range = calendar.monthrange(date_from.year, date_from.month)[1]
                date_to = datetime.strptime(str(slip.date_to), '%Y-%m-%d')
                month_range_2 = calendar.monthrange(date_to.year, date_to.month)[1]

                aa = date_from.month
                bb = date_to_days.month
                new_old = date_to.strftime('%Y-%m-01')
                new = datetime.strptime(str(new_old), '%Y-%m-%d')

                if aa == bb:
                    if month_range == date_to_days.day:
                        if date_to_days.day != 30: 
                           days = 30 - date_from.day + 1
                           slip.num_work_days = days
                        else:
                            days = 30 - date_from.day + 1
                            slip.num_work_days = days
                    else:
                        days = (date_to_days - date_from).days + 1
                        slip.num_work_days = days
                elif aa != bb:
                    a1 = 0.0
                    b1 = 0.0
                    # if month_range != 30:
                    a1 = 30 - date_from.day + 1

                    if month_range_2 == date_to_days.day:
                        # if date_to_days.day != 30:
                        b1 = 30 - new.day + 1
                    elif month_range_2 != date_to_days.day:
                        b1 = (date_to_days - new).days + 1  
                                
                    days = a1 + b1
                    slip.num_work_days = days 
                                     

            else:
                slip.num_work_days = 0



    @api.depends('line_ids')
    def _compute_net_amount(self):
        """
        A method to compute net salary amount
        """
        for rec in self:
            for line in rec.line_ids:
                if line.salary_rule_id.net_rule:
                    rec.net_amount = line.total

    def _get_payslip_lines(self):
        line_vals = []

        if any(self.mapped('ytd_computation')):
            last_ytd_payslips = self._get_last_ytd_payslips()
            code_set = set(self.struct_id.rule_ids.mapped('code'))
        else:
            last_ytd_payslips = defaultdict(lambda: self.env['hr.payslip'])
            code_set = set()
        ytd_payslips = reduce(
            lambda ytd_payslips, payslip: ytd_payslips | payslip, last_ytd_payslips.values(),
            self.env['hr.payslip']
        )

        line_values = ytd_payslips._get_line_values(code_set, ['ytd'])

        for payslip in self:
            if not payslip.contract_id:
                raise UserError(_("There's no contract set on payslip %(payslip)s for %(employee)s. Check that there is at least a contract set on the employee form.", payslip=payslip.name, employee=payslip.employee_id.name))

            localdict = self.env.context.get('force_payslip_localdict', None)
            if localdict is None:
                localdict = payslip._get_localdict()

            rules_dict = localdict['rules']
            result_rules_dict = localdict['result_rules']

            blacklisted_rule_ids = self.env.context.get('prevent_payslip_computation_line_ids', [])

            result = {}
            for rule in sorted(payslip.struct_id.rule_ids, key=lambda x: x.sequence):
                if rule.id in blacklisted_rule_ids:
                    continue
                localdict.update({
                    'result': None,
                    'result_qty': 1.0,
                    'result_rate': 100,
                    'result_name': False
                })
                if rule._satisfy_condition(localdict):
                    # Retrieve the line name in the employee's lang
                    employee_lang = payslip.employee_id.lang or self.env.lang
                    # This actually has an impact, don't remove this line
                    if rule.code in localdict['same_type_input_lines']:
                        for multi_line_rule in localdict['same_type_input_lines'][rule.code]:
                            localdict['inputs'][rule.code] = multi_line_rule
                            amount, qty, rate = rule._compute_rule(localdict)
                            tot_rule = payslip._get_payslip_line_total(amount, qty, rate, rule)

                            result_rules_dict[rule.code]['total'] += tot_rule
                            result_rules_dict[rule.code]['amount'] += tot_rule
                            result_rules_dict[rule.code]['quantity'] = 1
                            result_rules_dict[rule.code]['rate'] = 100
                            rules_dict[rule.code] = rule

                            localdict = rule.category_id._sum_salary_rule_category(localdict,
                                                                                   tot_rule)
                            rule_name = payslip._get_rule_name(localdict, rule, employee_lang)
                            line_vals.append({
                                'sequence': rule.sequence,
                                'code': rule.code,
                                'name':  rule_name,
                                'salary_rule_id': rule.id,
                                'contract_id': localdict['contract'].id,
                                'employee_id': localdict['employee'].id,
                                'amount': amount,
                                'quantity': qty,
                                'rate': rate,
                                'total': tot_rule,
                                'slip_id': payslip.id,
                                'ytd': line_values[rule.code][last_ytd_payslips[payslip].id]
                                    ['ytd'] + tot_rule,
                            })
                    else:
                        amount, qty, rate = rule._compute_rule(localdict)
                        #check if there is already a rule computed with that code
                        previous_amount = localdict.get(rule.code, 0.0)
                        #set/overwrite the amount computed for this rule in the localdict
                        tot_rule = payslip._get_payslip_line_total(amount, qty, rate, rule)
                        localdict[rule.code] = tot_rule
                        result_rules_dict[rule.code] = {'total': tot_rule, 'amount': amount, 'quantity': qty, 'rate': rate}
                        rules_dict[rule.code] = rule
                        # sum the amount for its salary category
                        localdict = rule.category_id._sum_salary_rule_category(localdict, tot_rule - previous_amount)
                        rule_name = payslip._get_rule_name(localdict, rule, employee_lang)
                        # create/overwrite the rule in the temporary results
                        result[rule.code] = {
                            'sequence': rule.sequence,
                            'code': rule.code,
                            'name': rule_name,
                            'salary_rule_id': rule.id,
                            'contract_id': localdict['contract'].id,
                            'employee_id': localdict['employee'].id,
                            'amount': amount,
                            'analytic_account_id': localdict['contract'].employee_id.department_id.account_analytic_id.id if localdict['contract'].employee_id.department_id.account_analytic_id
                             else rule.analytic_account_id.id or False,
                            'quantity': qty,
                            'rate': rate,
                            'total': tot_rule,
                            'slip_id': payslip.id,
                            'ytd': line_values[rule.code][last_ytd_payslips[payslip].id]
                                ['ytd'] + tot_rule,
                        }
            line_vals += list(result.values())
        return line_vals


    # def _get_payslip_lines(self):
    #     '''
    #        override get_payslip_lines to : 
    #         1. only show payslip lines with rules that appears_on_payslip = True
    #         2. change partner_id and analytic_account_id in payslip line
    #     '''

    #     def _sum_salary_rule_category(localdict, category, amount):
    #         if category.parent_id:
    #             localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
    #         localdict['categories'].dict[category.code] = localdict['categories'].dict.get(category.code, 0) + amount
    #         return localdict

    #     self.ensure_one()
    #     result = {}
    #     rules_dict = {}
    #     worked_days_dict = {line.code: line for line in self.worked_days_line_ids if line.code}
    #     inputs_dict = {line.code: line for line in self.input_line_ids if line.code}

    #     employee = self.employee_id
    #     contract = self.contract_id

    #     localdict = {
    #         **self._get_base_local_dict(),
    #         **{
    #             'categories': BrowsableObject(employee.id, {}, self.env),
    #             'rules': BrowsableObject(employee.id, rules_dict, self.env),
    #             'payslip': Payslips(employee.id, self, self.env),
    #             'worked_days': WorkedDays(employee.id, worked_days_dict, self.env),
    #             'inputs': InputLine(employee.id, inputs_dict, self.env),
    #             'employee': employee,
    #             'contract': contract
    #         }
    #     }
    #     for rule in sorted(self.struct_id.rule_ids, key=lambda x: x.sequence):
    #         localdict.update({
    #             'result': None,
    #             'result_qty': 1.0,
    #             'result_rate': 100})
    #         localdict['result_qty'] = float(safe_eval(rule.quantity, localdict))
    #         if rule._satisfy_condition(localdict):
    #             amount, qty, rate = rule._compute_rule(localdict)
    #             # check if there is already a rule computed with that code
    #             previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
    #             # set/overwrite the amount computed for this rule in the localdict
    #             tot_rule = amount * qty * rate / 100.0
    #             localdict[rule.code] = tot_rule
    #             rules_dict[rule.code] = rule
    #             # sum the amount for its salary category
    #             localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
    #             # create/overwrite the rule in the temporary results
    #             if rule.appears_on_payslip:
    #                 result[rule.code] = {
    #                     'sequence': rule.sequence,
    #                     'code': rule.code,
    #                     'name': rule.name,
    #                     'note': rule.note,
    #                     'salary_rule_id': rule.id,
    #                     'contract_id': contract.id,
    #                     'employee_id': employee.id,
    #                     'amount': amount,
    #                     'analytic_account_id': contract.employee_id.department_id.account_analytic_id.id if contract.employee_id.department_id.account_analytic_id
    #                     else rule.analytic_account_id.id or False,
    #                     'quantity': qty,
    #                     'rate': rate,
    #                     'slip_id': self.id,
    #                     'partner_id': contract.employee_id.address_home_id.id if rule.required_partner else False,

    #                 }

    #                 # 'analytic_account_id': contract.employee_id.department_id.account_analytic_id.id if contract.employee_id.department_id.account_analytic_id
    #                 # else rule.analytic_account_id.id or False,
    #     return result.values()

    @api.constrains('employee_id', 'date_from', 'date_to', 'state')
    def _check_employee_payslip(self):
      
        for rec in self:
            domain = [
                ('id', '!=', rec.id),
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'done'),
                ('date_from', '<=', rec.date_to),
                ('date_to', '>=', rec.date_from),
            ]
            
            overlapping_payslips = self.env['hr.payslip'].search_count(domain)
            
            if overlapping_payslips > 0:
                raise ValidationError(_(
                    "You cannot create overlapping payslips for %s in the period %s to %s!"
                ) % (rec.employee_id.name, rec.date_from, rec.date_to))
    def action_payslip_cancel(self):
        # if self.filtered(lambda slip: slip.state == 'done'):
        #     raise UserError(_("Cannot cancel a payslip that is done."))
        for rec in self:
            if rec.move_id and rec.move_id.state not in ['draft','cancel']:
                raise ValidationError(_("cancel the voucher or delete it before cancel!"))
            if rec.move_id and rec.move_id.state == 'draft': 
                rec.move_id.with_context(force_delete=True).sudo().unlink()
        return self.write({'state': 'cancel'})

    def write(self, vals):
        res = super(HrPayslip,self).write(vals)
        if vals.get('state',False) and vals['state'] == 'done':
            self.action_update_related_records()
        return res

    def action_update_related_records(self):
        """
        Function to be updated by process that calculated using payroll
        """

        return True

class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    payslip_run_id = fields.Many2one('hr.payslip.run', related='slip_id.payslip_run_id')
    partner_id = fields.Many2one('res.partner', related=False)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')




class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def compute_sheet(self):
        self.ensure_one()
        
        if not self.env.context.get('active_id'):
            from_date = fields.Date.to_date(self.env.context.get('default_date_start'))
            end_date = fields.Date.to_date(self.env.context.get('default_date_end'))
            payslip_run = self.env['hr.payslip.run'].create({
                'name': from_date.strftime('%B %Y'),
                'date_start': from_date,
                'date_end': end_date,
            })
        else:
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))

        if not self.employee_ids:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))


        contracts = self.employee_ids._get_contracts(payslip_run.date_start, payslip_run.date_end)
        date_start_dt = datetime.combine(payslip_run.date_start, time.min)
        date_end_dt = datetime.combine(payslip_run.date_end, time.max)
        contracts._generate_work_entries(date_start_dt, date_end_dt)

        
        return super(HrPayslipEmployees, self).compute_sheet()
