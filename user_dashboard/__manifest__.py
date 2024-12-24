{
    'name': "User Dashboard",
    'version': '17.0.0.0.0',
    'category': 'Dashboard',
    'summary': """Responsive HR Dashboard""",
    'description': """Overview employee data from hr Dashboard""",
    'author': "Ajay",
    'company': 'Sakshath Tech',
    'maintainer': 'Sakshath Tech',
    'website': "https://www.sakshath-technologies.com/",
    'depends': ['hr', 'hr_holidays', 'hr_timesheet',
                'hr_attendance', 'hr_timesheet_attendance',
                'hr_recruitment', 'event',
                'base'],
    'data': [
        'views/hr_inherit_view.xml',
        'views/hr_dashboard_menus.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'user_dashboard/static/src/css/user_dashboard.css',
            'user_dashboard/static/src/css/lib/nv.d3.css',
            'user_dashboard/static/src/js/user_dashboard.js',
            'user_dashboard/static/src/js/lib/d3.min.js',
            'user_dashboard/static/src/xml/user_dashboard_templates.xml',
            'https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.4/moment.min.js',
        ],
    },
    'external_dependencies': {'python': ['pandas']},
    'installable': True,
    'auto_install': False,
    'application': True,
}