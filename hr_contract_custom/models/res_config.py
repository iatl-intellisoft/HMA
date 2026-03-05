from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    hr_group_id = fields.Many2one('res.groups',string='Hr Group', related="company_id.hr_group_id",
    readonly=False ,
     ondelete='set null',)


class ResCompany(models.Model):
    _inherit = 'res.company' 
    
    
    hr_group_id = fields.Many2one('res.groups',string='Hr Group',ondelete='set null',)
        
