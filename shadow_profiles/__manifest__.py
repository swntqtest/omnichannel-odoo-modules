{
    'name': 'Shadow Profiles',
    'version': '18.0.1.0.0',
    'category': 'CRM',
    'summary': 'Track potential customers from social media channels',
    'description': """
        Shadow Profiles Module
        ======================
        Track and manage potential customer profiles from various channels:
        - Facebook
        - Instagram
        - WhatsApp
        - Telegram
        - Website
        - Other sources
    """,
    'author': 'Custom',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/shadow_profile_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
