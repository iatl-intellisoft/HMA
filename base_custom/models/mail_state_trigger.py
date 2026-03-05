from odoo import api, fields, models

class MailTruggier(models.Model):
    _inherit = 'mail.tracking.value'

    new_key_state = fields.Char('New Key State', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        
        for vals in vals_list:
            if vals.get('field_id'):
                field = self.env['ir.model.fields'].browse(vals['field_id'])
                if field.name == 'state' and field.ttype == 'selection':
                    vals['new_key_state'] = vals.get('new_value_char')
        
        return super(MailTruggier, self).create(vals_list)

    def getStateTriggers(self, model, res_id, states):
        
        track = []
        if model and res_id and states:
            for st in states:
                st_value = self.env['mail.tracking.value'].sudo().search([
                    ('field_id.name', '=', 'state'),
                    ('new_key_state', '=', st),
                    ('mail_message_id.model', '=', model),
                    ('mail_message_id.res_id', '=', res_id)
                ], order='create_date ASC', limit=1)

                if st_value:
                    author = st_value.mail_message_id.author_id.name or st_value.mail_message_id.create_uid.name
                    
                    track.append({
                        'state': st,
                        'username': author,
                        'date': st_value.create_date.strftime('%Y-%m-%d')
                    })

        return track

    models.BaseModel.getStateTriggers = getStateTriggers
