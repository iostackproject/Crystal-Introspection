class AbstractMetric(object):
    def __init__(self, logger, crystal_control, metric_name, server):
        self.logger = logger
        self.crystal_control = crystal_control
        self.metric_name = metric_name
        self.current_server = server
        
    def register_metric(self, key, value):
        """
        Send data to publish thread
        """
        routing_key = self.metric_name
        self.crystal_control.publish_metric(routing_key, key, value)
        
    def execute(self, request):
        """
        Execute Metric
        """
        raise NotImplementedError()