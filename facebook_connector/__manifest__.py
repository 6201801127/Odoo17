{
    'name': 'Facebook Lead Ads Integration',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Integrates Facebook Lead Ads with Odoo',
    'description': """
        Fetch leads from Facebook Lead Ads and store them in Odoo CRM.
    """,
    'depends': ['base', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
