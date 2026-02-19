from odoo import models, api
from odoo.exceptions import UserError


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    @api.model
    def create(self, vals):
        job_id = vals.get('job_id')

        if job_id:
            job = self.env['hr.job'].browse(job_id)
            if job.state != 'approved':
                raise UserError(
                    "لا يمكن إنشاء مرشح قبل اعتماد الوظيفة من المدير العام."
                )

        return super().create(vals)
