from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
import xlsxwriter
from io import BytesIO
import base64

class hrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    input_id = fields.Many2one('hr.input', 'Input/Expense')

class HrInput(models.Model):
    _name = 'hr.input'
    _description = 'HR Contract Inputs'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    name = fields.Char(string='Name')
    input_type_id = fields.Many2one('hr.payslip.input.type', string='Input/Expense', required=True, domain=[('code', 'in', ['ALIM', 'COMS', 'INDM', 'BONO', 'MLTA', 'PHIP', 'HEXT', 'PQUI', 'HSUP', 'MOVI', 'PENS'])])
    input_date = fields.Date(string='Input Date')
    amount = fields.Float(string='Amount')
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Nomina')
    state = fields.Selection([('draft','DRAFT'),('running','RUNNING'),('processed','PROCESSED'),('done','DONE')], default='draft')

    def publish_button(self):
        self.state = 'running'

    def draft_button(self):
        if self.state == 'running':
            self.state = 'draft'
        else:
            raise UserError(_('You can only set the state to draft when it is in running state.'))
        
    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_or_cancel(self):
        if any(self.filtered(lambda input: input.state not in ('draft'))):
            raise UserError(_('You cannot delete an input which is not draft!'))

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    _order = 'date_from desc, employee_id'

    def _get_inputs_line(self,contracts,date_from,date_to):
        self.input_line_ids = []
        res = []
        for contract in contracts:
            inputs_ids = self.env['hr.input'].search([
                                    ('input_date','<=',date_to),('input_date','>=',date_from),
                                    ('employee_id','=',contract.employee_id.id), ('state','=','running')])
            for inputs in inputs_ids:
                input_data = {
                    'name': inputs.name,
                    'input_type_id': inputs.input_type_id.id,
                    'code': inputs.input_type_id.code,
                    'contract_id': contract.id,
                    'amount': inputs.amount,
                    'input_id': inputs.id,
                    'payslip_id':self.id,
                }
                res.append(input_data)
        return res 
    
    def compute_sheet(self):
        for s in self:
            res = s._get_inputs_line(s.contract_id,s.date_from,s.date_to)
            if not s.input_line_ids and res:
                s.input_line_ids.create(res)
            else:
                for r in res:
                    cont = 0
                    for lines in s.input_line_ids:
                        if r['input_id'] == lines.input_id.id:
                            lines.update(r)
                            cont = 1
                            break;
                    if not cont:
                        s.input_line_ids.create([r])
            
            hr_inputs_to_update = self.env['hr.input'].search([
                ('id', 'in', [line['input_id'] for line in res]),
                ('state', '=', 'running')
            ])
            hr_inputs_to_update.write({'state': 'processed'})

            hr_inputs_to_update.write({'payslip_run_id': s.payslip_run_id.id})

            super(HrPayslip,s).compute_sheet()
    
    def action_payslip_paid(self):

        for payslip in self:
            
            date_from = payslip.date_from
            date_to = payslip.date_to
            employees = payslip.mapped('employee_id')
            
            hr_input_records = self.env['hr.input'].search([
                ('employee_id', 'in', employees.ids),
                ('input_date', '<=', date_to),
                ('input_date', '>=', date_from),
            ])

            hr_input_records.write({'state': 'done'})

        return super(HrPayslip, self).action_payslip_paid()
    
    def action_payslip_draft(self):

        for payslip in self:
            
            date_from = payslip.date_from
            date_to = payslip.date_to
            employees = payslip.mapped('employee_id')
            
            hr_input_records = self.env['hr.input'].search([
                ('employee_id', 'in', employees.ids),
                ('input_date', '<=', date_to),
                ('input_date', '>=', date_from),
            ])

            hr_input_records.write({'state': 'running'})

        return super(HrPayslip, self).action_payslip_draft()

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    input_id = fields.One2many('hr.input', 'payslip_run_id', string='Inputs')

    def unlink(self):
        # Antes de eliminar la ejecución de nómina, actualiza el estado de los hr.input vinculados.
        input_to_update = self.mapped('input_id').filtered(lambda input_rec: input_rec.state == 'processed')
        input_to_update.write({'state': 'running'})
        
        # Continúa con la eliminación de la ejecución de la nómina.
        return super(HrPayslipRun, self).unlink()
    
    def print_xlsx_payroll(self):
        file_data =  BytesIO()
        workbook = xlsxwriter.Workbook(file_data)
        query_totales = """select sum(hpl.total), hpl.name, hpl."sequence" from hr_payslip_run hpr 
                                join hr_payslip hp on hp.payslip_run_id =hpr.id
                                join hr_payslip_line hpl on hpl.slip_id = hp.id
                                join hr_employee he on hp.employee_id = he.id
                                join hr_salary_rule hsr on hpl.salary_rule_id = hsr.id
                                where hsr.appears_on_payslip """
        query = """select distinct(hpl.name), hpl."sequence" from hr_payslip_run hpr 
                            join hr_payslip hp on hp.payslip_run_id =hpr.id
                            join hr_payslip_line hpl on hpl.slip_id = hp.id
                            join hr_salary_rule hsr on hpl.salary_rule_id = hsr.id
                            where hpr.id=%s and hsr.appears_on_payslip
                            order by hpl.sequence """ %(self.id)
        name = self.name
        self.xslx_body(workbook,query_totales,query,name,False)
        workbook.close()
        file_data.seek(0)
        attachment = self.env['ir.attachment'].create({
            'datas': base64.b64encode(file_data.getvalue()),
            'name': self.name,
            'store_fname': self.name + '.xlsx',
        })
        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url += "/web/content/%s?download=true" %(attachment.id)
        return{
        "type": "ir.actions.act_url",
        "url": url,
        "target": "new",
        }
    
    def xslx_body(self, workbook, query_totales, query, name, comision):
        bold = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#067eb2'})
        bold.set_center_across()
        number = workbook.add_format({'num_format': '$#,##0.00', 'border': 1})
        number2 = workbook.add_format({'num_format': '$#,##0.00', 'border': 1, 'bg_color': '#067eb8', 'bold': True})
        border = workbook.add_format({'border': 1})
        condition = " and hpr.id=%s group by hpl.sequence, hpl.name" % (self.id)
        struct_id = False
        if comision:
            struct_id = self.env['res.config.settings'].sudo(1).search([], limit=1, order="id desc").struct_id
            if not struct_id:
                raise ValidationError(_('No ha registrado una estructura para comisiones en sus configuraciones.'))
            condition_2 = " and hp.struct_id=%s" % struct_id.id
            condition = condition_2 + condition
        col = 2
        colspan = 0
        sheet = workbook.add_worksheet(name)
        sheet.write(1, 4, name.upper())
        sheet.write(col, colspan, 'Mes')
        sheet.write(col, colspan + 1, self.date_start.month)
        sheet.write(col, colspan + 2, 'Periodo')
        sheet.write(col, colspan + 3, self.date_start.year)
        col += 1
        sheet.write(col, colspan, 'No.', bold)
        sheet.write(col, colspan + 1, 'Localidad', bold)
        sheet.write(col, colspan + 2, 'Area', bold)
        sheet.write(col, colspan + 3, 'Departamento', bold)
        sheet.write(col, colspan + 4, 'Empleado', bold)
        sheet.freeze_panes(col + 1, colspan + 5)
        sheet.write(col, colspan + 5, 'Cedula', bold)
        sheet.write(col, colspan + 6, 'Dias Trabajados', bold)
        sheet.write(col, colspan + 7, 'Sueldo', bold)
        self.env.cr.execute(query)
        inputs = self.env.cr.fetchall()
        cont = 7
        dtc = {}
        for line in inputs:
            cont += 1
            sheet.write(col, colspan + cont, line[0], bold)
            dtc['%s' % (line[0])] = colspan + cont
        address = ''
        no = 0
        col -= 1
        if not all(True if employee.work_location_id else False for employee in self.slip_ids.mapped('employee_id')):
            raise UserError("Alguno de los empleados no tiene configurada la ubicación de trabajo")

        lineas = sorted(self.slip_ids, key=lambda x: x.employee_id.work_location_id.name)

        for payslip in lineas:
            if struct_id == False or payslip.struct_id == struct_id:
                if address != payslip.employee_id.work_location_id.name:
                    col += 1
                    if address != '':
                        no = 0
                        sheet.write(col, colspan + 4, 'TOTAL %s' % address, bold)
                        self.env.cr.execute(query_totales + (" and he.work_location_id = %s" % payslip.employee_id.work_location_id.id) + condition)
                        totals = self.env.cr.fetchall()
                        cont = 8
                        for total in totals:
                            while (cont < dtc[total[1]]):
                                sheet.write(col, cont, 0.00, number2)
                                cont += 1
                            sheet.write(col, dtc[total[1]], abs(total[0]), number2)
                            cont += 1
                    address = payslip.employee_id.work_location_id.name
                    col += 1
                    sheet.merge_range(col, 0, col, 3, address, bold)
                no += 1
                col += 1
                if payslip.contract_id.department_id.parent_id:
                    department = payslip.contract_id.department_id.parent_id.name
                else:
                    department = payslip.contract_id.department_id.name
                sheet.write(col, colspan, no, border)
                sheet.write(col, colspan + 1, payslip.employee_id.work_location_id.name, border)
                sheet.write(col, colspan + 2, department, border)
                sheet.write(col, colspan + 3, payslip.contract_id.department_id.name, border)
                sheet.write(col, colspan + 4, payslip.contract_id.employee_id.name, border)
                sheet.write(col, colspan + 5, payslip.contract_id.employee_id.identification_id, border)
                for days in payslip.worked_days_line_ids:
                    if days.code == 'WORK100':
                        day = days.number_of_days
                sheet.write(col, colspan + 6, day, border)
                sheet.write(col, colspan + 7, payslip.contract_id.wage, number)
                cont = 8
                for lines in payslip.line_ids:
                    if lines.appears_on_payslip:
                        while (cont < dtc[lines.name]):
                            sheet.write(col, cont, 0.00, number)
                            cont += 1
                        sheet.write(col, dtc[lines.name], abs(float(lines.total)), number)
                        cont += 1

        col += 1
        sheet.write(col, colspan + 4, 'TOTAL %s' % address, bold)
        self.env.cr.execute(query_totales + (" and he.work_location_id = %s" % payslip.employee_id.work_location_id.id) + condition)