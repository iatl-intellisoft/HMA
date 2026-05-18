from odoo import api, fields, models, _
#from odoo.addons.hr_payroll.models.browsable_object import BrowsableObject, InputLine, WorkedDays, Payslips
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round
from collections import defaultdict

class DefaultDictPayroll(defaultdict):
    def __init__(self, employee_id, env, default_factory=dict):
        super().__init__(default_factory)
        self.employee_id = employee_id
        self.env = env

    def get(self, key, default=None):
        if key not in self and default is not None:
            self[key] = default
        return super().get(key, default)
class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    required_partner = fields.Boolean('Need Partner',
                                      help=' Total amount in this rule needed to be distributed by partner ')
    use_type = fields.Selection(string='Use Type', selection=[('general', 'General'), ('special', 'Special')],
                                default='general')
    net_rule = fields.Boolean(string='Net Rule', default=False)

    @api.constrains('net_rule', 'account_credit')
    def _check_net_rule(self):
        """
        A method to check net salary rule credit account
        """
        for rec in self:
            if rec.net_rule and not rec.account_credit:
                raise ValidationError(_('Must be enter credit account.'))

    @api.model
    def compute_rule_amount(self, emp_id):
        result_amount = 0.0

        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            localdict['categories'].dict[category.code] = localdict['categories'].dict.get(category.code, 0) + amount
            return localdict
        for rec in self:

            rec.ensure_one()
            result = {}
            rules_dict = {}
            # worked_days_dict = {line.code: line for line in self.worked_days_line_ids if line.code}
            # inputs_dict = {line.code: line for line in self.input_line_ids if line.code}
            employee = emp_id
            contract = rec.env['hr.contract'].search([('employee_id','=',employee.id),('state','=','running')], limit=1)

            
            localdict = {
                **rec._get_base_local_dict(),
                **{
                    # Pass employee_id and env; the factory defaults to 'dict' based on the class above
                    'categories': DefaultDictPayroll(employee.id, rec.env),
                    'rules': DefaultDictPayroll(employee.id, rec.env),
                    'payslip': DefaultDictPayroll(employee.id, rec.env),
                    'worked_days': False,
                    'inputs': DefaultDictPayroll(employee.id, rec.env),
                    'employee': employee,
                    'contract': contract
                }
            }
            for rule in sorted(rec.struct_id.rule_ids, key=lambda x: x.sequence):
                localdict.update({
                    'result': None,
                    'result_qty': 1.0,
                    'result_rate': 100})
                if rule._satisfy_condition(localdict):
                    amount, qty, rate = rule._compute_rule(localdict)
                    #check if there is already a rule computed with that code
                    previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                    #set/overwrite the amount computed for this rule in the localdict
                    tot_rule = amount * qty * rate / 100.0
                    localdict[rule.code] = tot_rule
                    rules_dict[rule.code] = rule
                    # sum the amount for its salary category
                    localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                    # create/overwrite the rule in the temporary results
            result_amount = localdict[rec.code]

        return result_amount

    

    def _get_base_local_dict(self):
        return {
            'float_round': float_round
        }
        
    # # inprogress
    # def compute_rule_amount(self, emp_id):
    #     def _sum_salary_rule_category(localdict, category, amount):
    #         if category.parent_id:
    #             localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
    #         localdict['categories'].dict[category.code] = localdict['categories'].dict.get(category.code, 0) + amount
    #         return localdict

    #     self.ensure_one()
    #     # result = {}
    #     rules_dict = {}
    #     result_amount = 0.0
    #     payslip = self.env['hr.payslip']
    #     # blacklist = []
    #     worked_days_dict = {line.code: line for line in payslip.worked_days_line_ids if line.code}
    #     # inputs_dict = {line.code: line for line in self.input_line_ids if line.code}

    #     employee = emp_id
    #     # contract = self.contract_id
    #     if emp_id.active:
    #         domain = [('employee_id', '=', emp_id.id),
    #                     ('state', 'in', ['open', 'offer'])]
    #     else:
    #         domain = [('employee_id', '=', emp_id.id)]
    #     contract = self.env['hr.contract'].search(domain,order = 'date_start desc' ,limit=1)
    #     if not contract and emp_id.active == True:
    #         raise ValidationError(_("There is no running contract for this Employee %s.") % (emp_id.name))

    #     # localdict = {
    #     #     # **self._get_base_local_dict(),
    #     #     **{
    #     #         'categories': BrowsableObject(employee.id, {}, self.env),
    #     #         'rules': BrowsableObject(employee.id, rules_dict, self.env),
    #     #         # 'payslip': False,
    #     #         # 'worked_days':False,
    #     #         # 'inputs': False,
    #     #         'employee': employee,
    #     #         'contract': contract
    #     #     }
    #     # }

    #     # struct_id = contract.struct_id
    #     rule_ids = self.env['hr.salary.rule'].search([('struct_id','=',contract.struct_id.id),('sequence','<=',self.sequence)])
    #     self.ensure_one()
    #     if self.id not in rule_ids.ids:
    #         rule_ids = rule_ids + self

    #     rules_list = rule_ids.filtered(
    #         lambda r: r.amount_select != 'code' or 
    #         (r.amount_select == 'code' and 
    #          not any(x in r.amount_python_compute for x in ['payslip', 'inputs', 'worked_days']))
    #     )

    #     result_amount = 0.0
        
    #     for rule in sorted(rules_list, key=lambda x: x.sequence):
    #         localdict.update({
    #             'result': None,
    #             'result_qty': 1.0,
    #             'result_rate': 100
    #         })

    #         if rule._satisfy_condition(localdict):
    #             amount, qty, rate = rule._compute_rule(localdict)
    #             previous_amount = localdict.get(rule.code, 0.0)
                
    #             tot_rule = amount * qty * rate / 100.0
    #             localdict[rule.code] = tot_rule
                
    #             # Update category totals
    #             localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)

    #             # If we reached the current rule, we can stop
    #             if rule.id == self.id:
    #                 break

    #     return localdict.get(self.code, 0.0)




class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    partner_id = fields.Many2one('res.partner', string='Salary partner',
                                 help="Eventual third party involved in the salary payment of the employees.")
