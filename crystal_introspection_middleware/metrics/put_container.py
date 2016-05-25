from abstract_metric import AbstractMetric

class GetTenant(AbstractMetric):
        
    def execute(self, request):
        """
        Execute Metric
        """
        if request.method == "PUT":
            if self.current_server == 'proxy':
                _, acc, cont, _ = request.split_path(4, 4, rest_with_last=True)
            else:
                _, _, acc, cont, _ = request.split_path(5, 5, rest_with_last=True)
                
            self.register_metric(acc+"/"+cont,1) 