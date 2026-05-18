from odoo import models, fields, api

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    birth_date = fields.Date(string="Birth Date") 
    age = fields.Integer(
            string="Age",
            compute="_compute_age",
            store=True
        )
    emergency_relation = fields.Char(string="Emergency Contact Relation")
    last_degree = fields.Char(string="Last Degree")
    specialization = fields.Char(string="Specialization")
    institution_name = fields.Char(string="Institution Name")
    graduation_year = fields.Date(string="Graduation Year")
    experience_ids = fields.One2many(
        'applicant.experience',
        'applicant_id',
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

    @api.depends('birth_date')
    def _compute_age(self):
        for rec in self:
            if rec.birth_date:
                today = fields.Date.today()
                rec.age = today.year - rec.birth_date.year
            else:
                rec.age = 0

   
    def create_employee_from_applicant(self):
        res = super().create_employee_from_applicant()
        for applicant in self:
            employee = self.env['hr.employee'].search([
                ('work_contact_id', '=', applicant.partner_id.id)
            ], limit=1)
            if employee:
                employee.write({
                    'birth_date': applicant.birth_date,
                    'age': applicant.age,
                    'emergency_relation': applicant.emergency_relation,
                    'last_degree': applicant.last_degree,
                    'specialization': applicant.specialization,
                    'institution_name': applicant.institution_name,
                    'graduation_year': applicant.graduation_year,
                    'years_experience': applicant.years_experience,
                    'last_company': applicant.last_company,
                    'previous_job_title': applicant.previous_job_title,
                    'work_from': applicant.work_from,
                    'work_to': applicant.work_to,
                    'personal_photo': applicant.personal_photo,
                    'national_id_copy': applicant.national_id_copy,
                    'certificates_pdf': applicant.certificates_pdf,
                })    
          
        return res   