import json
from odoo import http
from odoo.http import request, Response


class ContactCenterAPI(http.Controller):
    """REST API for Contact Center - Used by N8N"""

    def _json_response(self, data, status=200):
        """Return JSON response"""
        return Response(
            json.dumps(data, default=str),
            status=status,
            mimetype='application/json'
        )

    def _error_response(self, message, status=400):
        """Return error response"""
        return self._json_response({
            'success': False,
            'error': message
        }, status)

    def _success_response(self, data=None, message=None):
        """Return success response"""
        response = {'success': True}
        if data is not None:
            response['data'] = data
        if message:
            response['message'] = message
        return self._json_response(response)

    # ============== AGENT ENDPOINTS ==============

    @http.route('/api/v1/cc/agents', type='http', auth='api_key', methods=['GET'], csrf=False)
    def list_agents(self, **kwargs):
        """List all agents with optional filters"""
        try:
            domain = []

            if kwargs.get('status'):
                domain.append(('status', '=', kwargs['status']))
            if kwargs.get('team_id'):
                domain.append(('team_id', '=', int(kwargs['team_id'])))
            if kwargs.get('skill_code'):
                domain.append(('skill_ids.code', '=', kwargs['skill_code']))

            limit = int(kwargs.get('limit', 100))
            offset = int(kwargs.get('offset', 0))

            agents = request.env['cc.agent'].sudo().search(
                domain, limit=limit, offset=offset, order='name'
            )
            total = request.env['cc.agent'].sudo().search_count(domain)

            return self._success_response({
                'records': [a.to_dict() for a in agents],
                'total': total,
                'limit': limit,
                'offset': offset
            })
        except Exception as e:
            return self._error_response(str(e), 500)

    @http.route('/api/v1/cc/agents/available', type='http', auth='api_key', methods=['GET'], csrf=False)
    def get_available_agents(self, **kwargs):
        """Get available agents, optionally filtered by skill, team, or channel"""
        try:
            skill_code = kwargs.get('skill_code')
            team_id = int(kwargs['team_id']) if kwargs.get('team_id') else None
            channel = kwargs.get('channel')

            agents = request.env['cc.agent'].sudo().get_available_agents(
                skill_code=skill_code,
                team_id=team_id,
                channel=channel
            )

            return self._success_response({
                'records': [a.to_dict() for a in agents],
                'count': len(agents)
            })
        except Exception as e:
            return self._error_response(str(e), 500)

    @http.route('/api/v1/cc/agents/<int:agent_id>', type='http', auth='api_key', methods=['GET'], csrf=False)
    def get_agent(self, agent_id, **kwargs):
        """Get single agent"""
        try:
            agent = request.env['cc.agent'].sudo().browse(agent_id)
            if not agent.exists():
                return self._error_response('Agent not found', 404)
            return self._success_response(agent.to_dict())
        except Exception as e:
            return self._error_response(str(e), 500)

    @http.route('/api/v1/cc/agents/<int:agent_id>/status', type='json', auth='api_key', methods=['PUT'], csrf=False)
    def update_agent_status(self, agent_id, **kwargs):
        """Update agent status"""
        try:
            agent = request.env['cc.agent'].sudo().browse(agent_id)
            if not agent.exists():
                return {'success': False, 'error': 'Agent not found'}

            data = request.jsonrequest
            status = data.get('status')

            if status == 'available':
                agent.action_set_available()
            elif status == 'busy':
                agent.action_set_busy()
            elif status == 'on_break':
                agent.action_set_break()
            elif status == 'offline':
                agent.action_set_offline()
            elif status == 'after_call':
                agent.action_set_after_call()
            else:
                return {'success': False, 'error': 'Invalid status'}

            return {'success': True, 'data': agent.to_dict()}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ============== QUEUE ENDPOINTS ==============

    @http.route('/api/v1/cc/queues', type='http', auth='api_key', methods=['GET'], csrf=False)
    def list_queues(self, **kwargs):
        """List all queues"""
        try:
            domain = [('active', '=', True)]

            if kwargs.get('queue_type'):
                domain.append(('queue_type', '=', kwargs['queue_type']))

            queues = request.env['cc.queue'].sudo().search(domain, order='priority desc, name')

            return self._success_response({
                'records': [q.to_dict() for q in queues]
            })
        except Exception as e:
            return self._error_response(str(e), 500)

    @http.route('/api/v1/cc/queues/<int:queue_id>', type='http', auth='api_key', methods=['GET'], csrf=False)
    def get_queue(self, queue_id, **kwargs):
        """Get single queue with available agents"""
        try:
            queue = request.env['cc.queue'].sudo().browse(queue_id)
            if not queue.exists():
                return self._error_response('Queue not found', 404)

            data = queue.to_dict()
            data['available_agents_list'] = [
                a.to_dict() for a in queue.get_available_agents()
            ]
            return self._success_response(data)
        except Exception as e:
            return self._error_response(str(e), 500)

    # ============== ROUTING ENDPOINTS ==============

    @http.route('/api/v1/cc/route', type='json', auth='api_key', methods=['POST'], csrf=False)
    def route_interaction(self, **kwargs):
        """Route an interaction to the best available agent"""
        try:
            data = request.jsonrequest
            queue_code = data.get('queue_code')
            queue_id = data.get('queue_id')
            caller_number = data.get('caller_number')
            caller_name = data.get('caller_name')
            channel = data.get('channel', 'voice')
            interaction_type = data.get('interaction_type', 'inbound')
            shadow_profile_id = data.get('shadow_profile_id')

            Queue = request.env['cc.queue'].sudo()
            if queue_id:
                queue = Queue.browse(int(queue_id))
            elif queue_code:
                queue = Queue.search([('code', '=', queue_code)], limit=1)
            else:
                return {'success': False, 'error': 'queue_code or queue_id required'}

            if not queue.exists():
                return {'success': False, 'error': 'Queue not found'}

            # Find best agent
            agent = queue.route_to_agent()
            if not agent:
                # No agent available - queue the call
                call = request.env['cc.call'].sudo().create({
                    'queue_id': queue.id,
                    'channel': channel,
                    'interaction_type': interaction_type,
                    'caller_number': caller_number,
                    'caller_name': caller_name,
                    'shadow_profile_id': shadow_profile_id,
                    'status': 'queued',
                })
                queue.calls_waiting += 1
                return {
                    'success': True,
                    'routed': False,
                    'queued': True,
                    'call_id': call.id,
                    'message': 'No agents available, call queued'
                }

            # Create call record
            call = request.env['cc.call'].sudo().create({
                'queue_id': queue.id,
                'agent_id': agent.id,
                'channel': channel,
                'interaction_type': interaction_type,
                'caller_number': caller_number,
                'caller_name': caller_name,
                'shadow_profile_id': shadow_profile_id,
                'status': 'ringing',
            })

            # Update agent status
            if channel == 'chat':
                agent.increment_chat_count()
            else:
                agent.action_set_busy()

            return {
                'success': True,
                'routed': True,
                'queued': False,
                'call_id': call.id,
                'agent': agent.to_dict()
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ============== CALL ENDPOINTS ==============

    @http.route('/api/v1/cc/calls', type='http', auth='api_key', methods=['GET'], csrf=False)
    def list_calls(self, **kwargs):
        """List calls with filters"""
        try:
            domain = []

            if kwargs.get('status'):
                domain.append(('status', '=', kwargs['status']))
            if kwargs.get('agent_id'):
                domain.append(('agent_id', '=', int(kwargs['agent_id'])))
            if kwargs.get('queue_id'):
                domain.append(('queue_id', '=', int(kwargs['queue_id'])))
            if kwargs.get('channel'):
                domain.append(('channel', '=', kwargs['channel']))

            limit = int(kwargs.get('limit', 100))
            offset = int(kwargs.get('offset', 0))

            calls = request.env['cc.call'].sudo().search(
                domain, limit=limit, offset=offset, order='start_time desc'
            )
            total = request.env['cc.call'].sudo().search_count(domain)

            return self._success_response({
                'records': [c.to_dict() for c in calls],
                'total': total,
                'limit': limit,
                'offset': offset
            })
        except Exception as e:
            return self._error_response(str(e), 500)

    @http.route('/api/v1/cc/calls/<int:call_id>', type='http', auth='api_key', methods=['GET'], csrf=False)
    def get_call(self, call_id, **kwargs):
        """Get single call"""
        try:
            call = request.env['cc.call'].sudo().browse(call_id)
            if not call.exists():
                return self._error_response('Call not found', 404)
            return self._success_response(call.to_dict())
        except Exception as e:
            return self._error_response(str(e), 500)

    @http.route('/api/v1/cc/calls/<int:call_id>/answer', type='json', auth='api_key', methods=['POST'], csrf=False)
    def answer_call(self, call_id, **kwargs):
        """Answer a call"""
        try:
            call = request.env['cc.call'].sudo().browse(call_id)
            if not call.exists():
                return {'success': False, 'error': 'Call not found'}

            call.action_answer()
            if call.queue_id and call.queue_id.calls_waiting > 0:
                call.queue_id.calls_waiting -= 1

            return {'success': True, 'data': call.to_dict()}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/api/v1/cc/calls/<int:call_id>/complete', type='json', auth='api_key', methods=['POST'], csrf=False)
    def complete_call(self, call_id, **kwargs):
        """Complete a call"""
        try:
            call = request.env['cc.call'].sudo().browse(call_id)
            if not call.exists():
                return {'success': False, 'error': 'Call not found'}

            data = request.jsonrequest
            if data.get('disposition'):
                call.disposition = data['disposition']
            if data.get('notes'):
                call.notes = data['notes']
            if data.get('customer_rating'):
                call.customer_rating = data['customer_rating']

            call.action_complete()

            # Handle chat count
            if call.channel == 'chat' and call.agent_id:
                call.agent_id.decrement_chat_count()

            return {'success': True, 'data': call.to_dict()}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/api/v1/cc/calls/<int:call_id>/transfer', type='json', auth='api_key', methods=['POST'], csrf=False)
    def transfer_call(self, call_id, **kwargs):
        """Transfer a call to another agent"""
        try:
            call = request.env['cc.call'].sudo().browse(call_id)
            if not call.exists():
                return {'success': False, 'error': 'Call not found'}

            data = request.jsonrequest
            target_agent_id = data.get('target_agent_id')
            if not target_agent_id:
                return {'success': False, 'error': 'target_agent_id required'}

            new_call = call.action_transfer(target_agent_id)
            return {
                'success': True,
                'data': {
                    'original_call': call.to_dict(),
                    'new_call': new_call.to_dict() if new_call else None
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ============== TEAM ENDPOINTS ==============

    @http.route('/api/v1/cc/teams', type='http', auth='api_key', methods=['GET'], csrf=False)
    def list_teams(self, **kwargs):
        """List all teams"""
        try:
            teams = request.env['cc.team'].sudo().search([('active', '=', True)])
            return self._success_response({
                'records': [t.to_dict() for t in teams]
            })
        except Exception as e:
            return self._error_response(str(e), 500)

    @http.route('/api/v1/cc/teams/<int:team_id>', type='http', auth='api_key', methods=['GET'], csrf=False)
    def get_team(self, team_id, **kwargs):
        """Get single team with agents"""
        try:
            team = request.env['cc.team'].sudo().browse(team_id)
            if not team.exists():
                return self._error_response('Team not found', 404)

            data = team.to_dict()
            data['agents'] = [a.to_dict() for a in team.agent_ids]
            return self._success_response(data)
        except Exception as e:
            return self._error_response(str(e), 500)

    # ============== SKILL ENDPOINTS ==============

    @http.route('/api/v1/cc/skills', type='http', auth='api_key', methods=['GET'], csrf=False)
    def list_skills(self, **kwargs):
        """List all skills"""
        try:
            skills = request.env['cc.skill'].sudo().search([('active', '=', True)])
            return self._success_response({
                'records': [s.to_dict() for s in skills]
            })
        except Exception as e:
            return self._error_response(str(e), 500)

    # ============== SHIFT ENDPOINTS ==============

    @http.route('/api/v1/cc/shifts', type='http', auth='api_key', methods=['GET'], csrf=False)
    def list_shifts(self, **kwargs):
        """List shifts with filters"""
        try:
            domain = []

            if kwargs.get('agent_id'):
                domain.append(('agent_id', '=', int(kwargs['agent_id'])))
            if kwargs.get('date'):
                domain.append(('date', '=', kwargs['date']))
            if kwargs.get('status'):
                domain.append(('status', '=', kwargs['status']))

            shifts = request.env['cc.shift'].sudo().search(domain, order='date desc, start_time')

            return self._success_response({
                'records': [s.to_dict() for s in shifts]
            })
        except Exception as e:
            return self._error_response(str(e), 500)

    @http.route('/api/v1/cc/shifts/<int:shift_id>/start', type='json', auth='api_key', methods=['POST'], csrf=False)
    def start_shift(self, shift_id, **kwargs):
        """Start a shift"""
        try:
            shift = request.env['cc.shift'].sudo().browse(shift_id)
            if not shift.exists():
                return {'success': False, 'error': 'Shift not found'}

            shift.action_start_shift()
            return {'success': True, 'data': shift.to_dict()}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/api/v1/cc/shifts/<int:shift_id>/end', type='json', auth='api_key', methods=['POST'], csrf=False)
    def end_shift(self, shift_id, **kwargs):
        """End a shift"""
        try:
            shift = request.env['cc.shift'].sudo().browse(shift_id)
            if not shift.exists():
                return {'success': False, 'error': 'Shift not found'}

            shift.action_end_shift()
            return {'success': True, 'data': shift.to_dict()}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ============== STATS ENDPOINT ==============

    @http.route('/api/v1/cc/stats', type='http', auth='api_key', methods=['GET'], csrf=False)
    def get_stats(self, **kwargs):
        """Get contact center statistics"""
        try:
            Agent = request.env['cc.agent'].sudo()
            Call = request.env['cc.call'].sudo()
            Queue = request.env['cc.queue'].sudo()

            stats = {
                'agents': {
                    'total': Agent.search_count([('active', '=', True)]),
                    'available': Agent.search_count([('status', '=', 'available')]),
                    'busy': Agent.search_count([('status', '=', 'busy')]),
                    'on_break': Agent.search_count([('status', '=', 'on_break')]),
                    'offline': Agent.search_count([('status', '=', 'offline')]),
                },
                'calls': {
                    'queued': Call.search_count([('status', '=', 'queued')]),
                    'in_progress': Call.search_count([('status', '=', 'in_progress')]),
                    'completed_today': Call.search_count([
                        ('status', '=', 'completed'),
                        ('end_time', '>=', kwargs.get('date', False) or False)
                    ]) if kwargs.get('date') else 0,
                },
                'queues': {
                    'total': Queue.search_count([('active', '=', True)]),
                    'total_waiting': sum(Queue.search([('active', '=', True)]).mapped('calls_waiting')),
                }
            }
            return self._success_response(stats)
        except Exception as e:
            return self._error_response(str(e), 500)
