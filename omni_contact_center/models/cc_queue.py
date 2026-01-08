from odoo import models, fields, api


class CCQueue(models.Model):
    _name = 'cc.queue'
    _description = 'Contact Center Queue'
    _order = 'priority desc, name'

    name = fields.Char(string='Queue Name', required=True, index=True)
    code = fields.Char(string='Code', required=True, index=True)
    description = fields.Text(string='Description')

    active = fields.Boolean(string='Active', default=True)
    priority = fields.Integer(string='Priority', default=10)

    # Queue type
    queue_type = fields.Selection([
        ('voice', 'Voice'),
        ('chat', 'Chat'),
        ('email', 'Email'),
        ('social', 'Social Media'),
        ('mixed', 'Mixed'),
    ], string='Queue Type', default='voice', required=True)

    # Routing strategy
    routing_strategy = fields.Selection([
        ('round_robin', 'Round Robin'),
        ('least_busy', 'Least Busy'),
        ('skill_based', 'Skill Based'),
        ('priority', 'Priority'),
        ('random', 'Random'),
    ], string='Routing Strategy', default='round_robin', required=True)

    # Required skill for this queue
    required_skill_ids = fields.Many2many(
        'cc.skill',
        'cc_queue_skill_rel',
        'queue_id',
        'skill_id',
        string='Required Skills'
    )

    # Teams assigned to this queue
    team_ids = fields.Many2many(
        'cc.team',
        'cc_team_queue_rel',
        'queue_id',
        'team_id',
        string='Assigned Teams'
    )

    # SLA settings
    sla_answer_seconds = fields.Integer(
        string='SLA Answer Time (seconds)',
        default=30
    )
    sla_abandon_seconds = fields.Integer(
        string='Max Wait Time (seconds)',
        default=300
    )

    # Statistics
    calls_waiting = fields.Integer(string='Calls Waiting', default=0)
    avg_wait_time = fields.Float(string='Avg Wait Time (sec)', default=0.0)
    avg_handle_time = fields.Float(string='Avg Handle Time (sec)', default=0.0)

    # Working hours
    is_24_7 = fields.Boolean(string='24/7 Operation', default=False)
    working_hours_start = fields.Float(string='Start Hour', default=8.0)
    working_hours_end = fields.Float(string='End Hour', default=17.0)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Queue code must be unique!'),
    ]

    def get_available_agents(self):
        """Get available agents for this queue based on routing strategy"""
        self.ensure_one()

        # Get agents from assigned teams
        agents = self.env['cc.agent']
        for team in self.team_ids:
            agents |= team.agent_ids

        # Filter by availability
        agents = agents.filtered(lambda a: a.status == 'available')

        # Filter by channel capability
        channel_map = {
            'voice': 'can_voice',
            'chat': 'can_chat',
            'email': 'can_email',
            'social': 'can_social',
        }
        if self.queue_type in channel_map:
            field_name = channel_map[self.queue_type]
            agents = agents.filtered(lambda a: getattr(a, field_name, False))

        # Filter by required skills
        if self.required_skill_ids:
            required_codes = set(self.required_skill_ids.mapped('code'))
            agents = agents.filtered(
                lambda a: required_codes.issubset(set(a.skill_ids.mapped('code')))
            )

        # For chat, also check capacity
        if self.queue_type == 'chat':
            agents = agents.filtered(
                lambda a: a.current_chats < a.max_concurrent_chats
            )

        return agents

    def route_to_agent(self):
        """Route to best available agent based on strategy"""
        self.ensure_one()
        agents = self.get_available_agents()

        if not agents:
            return False

        if self.routing_strategy == 'round_robin':
            # Sort by last call time (oldest first)
            return agents.sorted(
                key=lambda a: a.last_call_time or fields.Datetime.now(),
                reverse=False
            )[:1]

        elif self.routing_strategy == 'least_busy':
            # Sort by current chats (least first)
            return agents.sorted(key=lambda a: a.current_chats)[:1]

        elif self.routing_strategy == 'skill_based':
            # Sort by skill count (most skills first)
            return agents.sorted(
                key=lambda a: len(a.skill_ids),
                reverse=True
            )[:1]

        elif self.routing_strategy == 'priority':
            # Sort by team priority (if applicable)
            return agents[:1]

        elif self.routing_strategy == 'random':
            import random
            return random.choice(agents) if agents else False

        return agents[:1] if agents else False

    def to_dict(self):
        """Convert to dictionary for API response"""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'queue_type': self.queue_type,
            'routing_strategy': self.routing_strategy,
            'priority': self.priority,
            'required_skill_ids': self.required_skill_ids.ids,
            'required_skills': self.required_skill_ids.mapped('name'),
            'team_ids': self.team_ids.ids,
            'sla_answer_seconds': self.sla_answer_seconds,
            'sla_abandon_seconds': self.sla_abandon_seconds,
            'calls_waiting': self.calls_waiting,
            'avg_wait_time': self.avg_wait_time,
            'avg_handle_time': self.avg_handle_time,
            'is_24_7': self.is_24_7,
            'available_agents': len(self.get_available_agents()),
        }
