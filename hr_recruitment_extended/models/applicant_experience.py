from odoo import models, fields

class ApplicantExperience(models.Model):
    _name = 'applicant.experience'
    _description = 'Applicant Experience'

    applicant_id = fields.Many2one(
        'hr.applicant',
        string="Applicant",
        ondelete='cascade'
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        ondelete='cascade'
    )
    company_name = fields.Char("Company Name")
    job_title = fields.Char("Job Title")
    date_from = fields.Date("Date From")
    date_to = fields.Date("Date To")
