from odoo import fields, models, api, _

class HrPayslipInputType(models.Model):
    _inherit = 'hr.salary.rule.category'

    @api.model
    def _delete_salary_rule_category(self):
        structure = self.search([('code', 'in', ['BASIC' ,'GROSS' ,'COMP', 'DED', 'ALW', 'ALW'])])
        if structure:
            structure.unlink()