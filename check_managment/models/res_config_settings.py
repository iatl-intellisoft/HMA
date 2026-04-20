from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_receivable = fields.Many2one('account.account','Account Receivable' )
    account_payable = fields.Many2one('account.account','Account payable' )
    users_ids = fields.Many2many('res.users',string='Users')
    post_entry = fields.Boolean('Post Check Followup Entry')
    check_grace_period = fields.Integer("check grace period") 



class ConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    check_grace_period = fields.Integer("check grace period",related='company_id.check_grace_period',readonly=False) 

    account_receivable = fields.Many2one('account.account','Account Receivable' 
    	                                 , related='company_id.account_receivable' , 
    	                                   domain="[('account_type','=','asset_receivable')]",readonly=False)
    account_payable = fields.Many2one('account.account','Account payable' 
    	                                 ,related='company_id.account_payable' ,
    	                                   domain="[('account_type','=','liability_payable')]" , readonly=False)

    company_id = fields.Many2one('res.company','Company')
    users_ids = fields.Many2many('res.users',string='Users'
                                ,related='company_id.users_ids', readonly=False )
    post_entry = fields.Boolean(string="Post Check Followup Entry", related='company_id.post_entry',readonly=False )





