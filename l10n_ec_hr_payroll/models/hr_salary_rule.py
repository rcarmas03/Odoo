from odoo import api, fields, models

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    @api.model
    def _delete_salary_rules(self):
        structure = self.search([('code', 'in', ['GROSS', 'ATTACH_SALARY', 'CHILD_SUPPORT', 'ASSIG_SALARY', 'DEDUCTION', 'REIMBURSEMENT'])])
        if structure:
            structure.unlink()

    @api.model
    def _delete_salary_rules2(self):
        structure = self.search([('name','in', ['Salario básico total','Salario neto'])])
        if structure:
            structure.unlink()