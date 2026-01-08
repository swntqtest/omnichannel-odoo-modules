{
    'name': 'Omni Contact Center',
    'version': '18.0.1.0.0',
    'category': 'Operations',
    'summary': 'Contact Center Management - Teams, Agents, Queues, Skills',
    'description': """
        Omni Contact Center Module
        ==========================
        Manage contact center operations with:

        Features:
        - Team management
        - Agent management with skills
        - Queue routing
        - Shift management
        - Call/Chat logging
        - REST API for N8N integration

        Models:
        - cc.team: Teams
        - cc.agent: Agents (extends hr.employee)
        - cc.skill: Agent skills
        - cc.queue: Routing queues
        - cc.shift: Work shifts
        - cc.call: Call/Chat logs

        API Endpoints:
        - GET/POST /api/v1/cc/agents
        - GET /api/v1/cc/agents/available
        - PUT /api/v1/cc/agents/<id>/status
        - POST /api/v1/cc/route
        - GET /api/v1/cc/queues
    """,
    'author': 'Omnichannel Team',
    'website': 'https://github.com/swntqtest/omnichannel-odoo-modules',
    'depends': ['base', 'hr', 'shadow_profiles'],
    'data': [
        'security/ir.model.access.csv',
        'data/cc_sequence.xml',
        'views/cc_agent_views.xml',
        'views/cc_queue_views.xml',
        'views/cc_team_views.xml',
        'views/cc_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
