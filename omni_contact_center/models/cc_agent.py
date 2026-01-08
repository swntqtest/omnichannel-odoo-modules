from odoo import models, fields, api


class CCAgent(models.Model):
    _name = 'cc.agent'
    _description = 'Contact Center Agent'
    _inherits = {'hr.employee': 'employee_id'}
    _order = 'name'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        auto_join=True
    )

    # Agent specific fields
    agent_code = fields.Char(string='Agent Code', index=True)
    extension = fields.Char(string='Extension Number')

    status = fields.Selection([
        ('offline', 'Offline'),
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('on_break', 'On Break'),
        ('after_call', 'After Call Work'),
    ], string='Status', default='offline', required=True, index=True)

    # Channels the agent can handle
    channel_ids = fields.Selection([
        ('voice', 'Voice'),
        ('chat', 'Chat'),
        ('email', 'Email'),
        ('social', 'Social Media'),
    ], string='Primary Channel', default='voice')

    can_voice = fields.Boolean(string='Can Handle Voice', default=True)
    can_chat = fields.Boolean(string='Can Handle Chat', default=True)
    can_email = fields.Boolean(string='Can Handle Email', default=False)
    can_social = fields.Boolean(string='Can Handle Social', default=False)

    # Team & Skills
    team_id = fields.Many2one(
        'cc.team',
        string='Team',
        ondelete='set null',
        index=True
    )

    skill_ids = fields.Many2many(
        'cc.skill',
        'cc_agent_skill_rel',
        'agent_id',
        'skill_id',
        string='Skills'
    )

    # Capacity
    max_concurrent_chats = fields.Integer(
        string='Max Concurrent Chats',
        default=3
    )
    current_chats = fields.Integer(
        string='Current Chats',
        default=0
    )

    # Statistics
    total_calls = fields.Integer(string='Total Calls', default=0)
    total_chats = fields.Integer(string='Total Chats', default=0)
    avg_handle_time = fields.Float(string='Avg Handle Time (min)', default=0.0)
    avg_rating = fields.Float(string='Avg Rating', default=0.0)

    # Timestamps
    last_status_change = fields.Datetime(string='Last Status Change')
    last_call_time = fields.Datetime(string='Last Call Time')

    # Shift
    current_shift_id = fields.Many2one(
        'cc.shift',
        string='Current Shift',
        ondelete='set null'
    )

    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('agent_code_unique', 'unique(agent_code)', 'Agent code must be unique!'),
        ('extension_unique', 'unique(extension)', 'Extension number must be unique!'),
    ]

    def action_set_available(self):
        """Set agent status to available"""
        self.write({
            'status': 'available',
            'last_status_change': fields.Datetime.now()
        })

    def action_set_busy(self):
        """Set agent status to busy"""
        self.write({
            'status': 'busy',
            'last_status_change': fields.Datetime.now()
        })

    def action_set_break(self):
        """Set agent status to on break"""
        self.write({
            'status': 'on_break',
            'last_status_change': fields.Datetime.now()
        })

    def action_set_offline(self):
        """Set agent status to offline"""
        self.write({
            'status': 'offline',
            'last_status_change': fields.Datetime.now()
        })

    def action_set_after_call(self):
        """Set agent status to after call work"""
        self.write({
            'status': 'after_call',
            'last_status_change': fields.Datetime.now()
        })

    @api.model
    def get_available_agents(self, skill_code=None, team_id=None, channel=None):
        """Get list of available agents, optionally filtered by skill, team, or channel"""
        domain = [('status', '=', 'available')]

        if team_id:
            domain.append(('team_id', '=', team_id))

        if channel:
            channel_field_map = {
                'voice': 'can_voice',
                'chat': 'can_chat',
                'email': 'can_email',
                'social': 'can_social',
            }
            if channel in channel_field_map:
                domain.append((channel_field_map[channel], '=', True))
                # For chat, also check capacity
                if channel == 'chat':
                    agents = self.search(domain)
                    return agents.filtered(
                        lambda a: a.current_chats < a.max_concurrent_chats
                    )

        agents = self.search(domain)

        if skill_code:
            agents = agents.filtered(
                lambda a: skill_code in a.skill_ids.mapped('code')
            )

        return agents

    def increment_chat_count(self):
        """Increment current chat count"""
        for agent in self:
            agent.current_chats += 1
            if agent.current_chats >= agent.max_concurrent_chats:
                agent.action_set_busy()

    def decrement_chat_count(self):
        """Decrement current chat count"""
        for agent in self:
            if agent.current_chats > 0:
                agent.current_chats -= 1
            if agent.current_chats < agent.max_concurrent_chats and agent.status == 'busy':
                agent.action_set_available()

    def to_dict(self):
        """Convert to dictionary for API response"""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'agent_code': self.agent_code,
            'extension': self.extension,
            'status': self.status,
            'team_id': self.team_id.id if self.team_id else None,
            'team_name': self.team_id.name if self.team_id else None,
            'skill_ids': self.skill_ids.ids,
            'skills': self.skill_ids.mapped('name'),
            'can_voice': self.can_voice,
            'can_chat': self.can_chat,
            'can_email': self.can_email,
            'can_social': self.can_social,
            'max_concurrent_chats': self.max_concurrent_chats,
            'current_chats': self.current_chats,
            'total_calls': self.total_calls,
            'total_chats': self.total_chats,
            'avg_handle_time': self.avg_handle_time,
            'avg_rating': self.avg_rating,
            'last_status_change': self.last_status_change.isoformat() if self.last_status_change else None,
        }
