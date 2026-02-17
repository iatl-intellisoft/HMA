from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    birth_date = fields.Date(string="Birth Date") 
    age = fields.Integer(string="Age")
    emergency_relation = fields.Char(string="Emergency Contact Relation")
    last_degree = fields.Char(string="Last Degree")
    specialization = fields.Char(string="Specialization")
    institution_name = fields.Char(string="Institution Name")  
    graduation_year = fields.Date(string="Graduation Year")
    experience_ids = fields.One2many(
        'applicant.experience',
        'employee_id',
        string="Experiences"
    )
    years_experience = fields.Float(string="Years of Experience")
    last_company = fields.Char(string="Last Company")
    previous_job_title = fields.Char(string="Previous Job Title")
    work_from = fields.Date(string="Work From")
    work_to = fields.Date(string="Work To") 
    personal_photo = fields.Binary(string="Personal Photo")
    national_id_copy = fields.Binary(string="National ID Copy")
    certificates_pdf = fields.Binary(string="Certificates")