{
    'name': 'Ecuadorian - Payroll',
    'icon': '/l10n_ec/static/description/icon.png',
    'version': '1.0',
    'summary': 'Custom Payroll Module for Ecuador',
    'description': 'This module customizes the HR Payroll for Ecuador.',
    'category': 'Human Resources/Payroll',
    'depends': ['hr_payroll', 'hr_work_entry_contract_enterprise'],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_payslip_input_type.xml',
        'data/salary_rule_category.xml',
        'data/payroll_structure_type.xml',
        'data/hr_salary_rule.xml',
        'data/hr_payroll_data.xml',
        'views/hr_input_views.xml',
        'views/hr_payslip_run_views.xml',
        'views/hr_employee_views.xml'
    ],
    'installable': True,
    'auto_install': False,
    'license': 'OEEL-1',
}