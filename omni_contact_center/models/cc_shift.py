from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CCShift(models.Model):
    _name = 'cc.shift'
    _description = 'Contact Center Shift'
    _order = 'date desc, start_time'

    name = fields.Char(string='Shift Name', compute='_compute_name', store=True)

    agent_id = fields.Many2one(
        'cc.agent',
        string='Agent',
        required=True,
        ondelete='cascade',
        index=True
    )

    date = fields.Date(string='Date', required=True, index=True)

    start_time = fields.Float(string='Start Time', required=True)
    end_time = fields.Float(string='End Time', required=True)

    # Actual times
    actual_start = fields.Datetime(string='Actual Start')
    actual_end = fields.Datetime(string='Actual End')

    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='scheduled', required=True, index=True)

    # Break times
    break_duration = fields.Float(string='Break Duration (hours)', default=1.0)
    break_taken = fields.Float(string='Break Taken (hours)', default=0.0)

    # Notes
    notes = fields.Text(string='Notes')

    # Team (for reference)
    team_id = fields.Many2one(
        related='agent_id.team_id',
        string='Team',
        store=True
    )

    @api.depends('agent_id', 'date', 'start_time', 'end_time')
    def _compute_name(self):
        for record in self:
            if record.agent_id and record.date:
                start_str = self._float_to_time_str(record.start_time)
                end_str = self._float_to_time_str(record.end_time)
                record.name = f"{record.agent_id.name} - {record.date} ({start_str}-{end_str})"
            else:
                record.name = "New Shift"

    @staticmethod
    def _float_to_time_str(float_time):
        """Convert float time to HH:MM string"""
        hours = int(float_time)
        minutes = int((float_time - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for record in self:
            if record.start_time >= record.end_time:
                raise ValidationError("End time must be after start time!")
            if record.start_time < 0 or record.start_time >= 24:
                raise ValidationError("Start time must be between 0 and 24!")
            if record.end_time < 0 or record.end_time > 24:
                raise ValidationError("End time must be between 0 and 24!")

    def action_start_shift(self):
        """Start the shift"""
        self.write({
            'status': 'in_progress',
            'actual_start': fields.Datetime.now()
        })
        # Also set agent to available
        self.agent_id.action_set_available()
        self.agent_id.current_shift_id = self.id

    def action_end_shift(self):
        """End the shift"""
        self.write({
            'status': 'completed',
            'actual_end': fields.Datetime.now()
        })
        # Set agent to offline
        self.agent_id.action_set_offline()
        self.agent_id.current_shift_id = False

    def action_cancel_shift(self):
        """Cancel the shift"""
        self.write({'status': 'cancelled'})

    def to_dict(self):
        """Convert to dictionary for API response"""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'agent_id': self.agent_id.id,
            'agent_name': self.agent_id.name,
            'date': self.date.isoformat() if self.date else None,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'start_time_str': self._float_to_time_str(self.start_time),
            'end_time_str': self._float_to_time_str(self.end_time),
            'status': self.status,
            'actual_start': self.actual_start.isoformat() if self.actual_start else None,
            'actual_end': self.actual_end.isoformat() if self.actual_end else None,
            'break_duration': self.break_duration,
            'break_taken': self.break_taken,
            'team_id': self.team_id.id if self.team_id else None,
        }
