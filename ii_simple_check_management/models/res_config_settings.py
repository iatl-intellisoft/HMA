from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_receivable = fields.Many2one('account.account','Account Receivable' )
    account_payable = fields.Many2one('account.account','Account payable' )


class ConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_receivable = fields.Many2one('account.account','Account Receivable' 
    	                                 , related='company_id.account_receivable' , 
    	                                   domain="[('account_type','=','asset_receivable')]",readonly=False)
    account_payable = fields.Many2one('account.account','Account payable' 
    	                                 ,related='company_id.account_payable' ,
    	                                   domain="[('account_type','=','liability_payable')]" , readonly=False)
  

