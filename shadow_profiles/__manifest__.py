{
    'name': 'Shadow Profiles',
    'version': '18.0.2.0.0',
    'category': 'CRM',
    'summary': 'Track potential customers from social media channels with REST API',
    'description': """
        Shadow Profiles Module
        ======================
        Track and manage potential customer profiles from various channels.

        Channels Supported:
        - Facebook
        - Instagram
        - WhatsApp
        - Telegram
        - Phone
        - Website

        Features:
        - Shadow Profile management with status workflow
        - Conversation tracking per profile
        - Multi-channel support
        - REST API for N8N integration
        - Auto-conversion to res.partner

        Status Workflow:
        Anonymous → Qualified → Pending Registration → Registered

        API Endpoints:
        - GET/POST /api/v1/shadow
        - GET/PUT/DELETE /api/v1/shadow/<id>
        - GET /api/v1/shadow/search
        - POST /api/v1/shadow/find-or-create
        - POST /api/v1/shadow/<id>/qualify
        - POST /api/v1/shadow/<id>/convert
        - GET /api/v1/shadow/stats
    """,
    'author': 'Omnichannel Team',
    'website': 'https://github.com/swntqtest/omnichannel-odoo-modules',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/shadow_conversation_views.xml',
        'views/shadow_profile_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
