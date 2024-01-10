from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    name_employee = fields.Char(string= 'Names')
    surname_employee = fields.Char (string = 'Surnames')
    payment_thirteenth_salary = fields.Boolean(string='Menzualize Thirteenth')
    payment_fourteenth_salary = fields.Boolean(string='Menzualize Fourteenth')
    payment_reserve_funds = fields.Boolean(string='Menzualize Reserve Funds')

    @api.model
    def create(self, vals):
        if 'name_employee' in vals and 'surname_employee' in vals:
            vals['name'] = vals['name_employee'] + ' ' + vals['surname_employee']
        return super(HrEmployee, self).create(vals)

    def write(self, vals):
        if ('name_employee' in vals or 'surname_employee' in vals) and ('name' not in vals or not vals.get('name')):
            if vals.get('name_employee') and vals.get('surname_employee'):
                vals['name'] = vals['name_employee'] + ' ' + vals['surname_employee']
        return super(HrEmployee, self).write(vals)
    
    def action_create_user(self):
        self.ensure_one()
        if self.user_id:
            raise ValidationError(_("This employee already has a user."))

        # Asegúrate de que name_employee y surname_employee tengan valores válidos
        if not self.name_employee or not self.surname_employee:
            raise ValidationError(_("Invalid employee name or surname."))

        # Concatenating name_employee and surname_employee if name is not present
        if not self.name:
            self.name = self.name_employee + ' ' + self.surname_employee
        
        return {
            'name': _('Create User'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'form',
            'view_id': self.env.ref('hr.view_users_simple_form').id,
            'target': 'new',
            'context': {
                'default_create_employee_id': self.id,
                'default_name': self.name,
                'default_phone': self.work_phone,
                'default_mobile': self.mobile_phone,
                'default_login': self.work_email,
            }
        }