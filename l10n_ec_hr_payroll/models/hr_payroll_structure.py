from odoo import api, fields, models

class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    @api.model
    def _delete_payroll_structures(self):
        structure = self.search([('name','in', ['Regular Pay','Worker Pay'])])
        if structure:
            structure.unlink()