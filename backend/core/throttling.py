from rest_framework.throttling import SimpleRateThrottle

class AgentRegisterThrottle(SimpleRateThrottle):
    scope = 'agent_register'

    def get_cache_key(self, request, view):
        # Throttle registration requests by IP address
        return self.get_ident(request)

class AgentHeartbeatThrottle(SimpleRateThrottle):
    scope = 'agent_heartbeat'

    def get_cache_key(self, request, view):
        # request.user is the Machine object in ApiKeyAuthentication.
        # Use the machine ID to uniquely identify the agent.
        if request.user and hasattr(request.user, 'id'):
            return f"throttle_{self.scope}_{request.user.id}"
        return self.get_ident(request)

class AgentMetricsThrottle(SimpleRateThrottle):
    scope = 'agent_metrics'

    def get_cache_key(self, request, view):
        if request.user and hasattr(request.user, 'id'):
            return f"throttle_{self.scope}_{request.user.id}"
        return self.get_ident(request)
