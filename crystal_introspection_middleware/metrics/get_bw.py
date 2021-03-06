from abstract_metric import AbstractMetric


class GetBw(AbstractMetric):
        
    def execute(self):
        """
        Execute Metric
        """ 
        if self.method == "GET" and self._is_object_request():
            ''' When we intercept the request, all chunks will enter by run_metric method ''' 
            self._intercept_get()
            
        ''' It is necessary to return the intercepted response '''          
        return self.response
 
    def on_read(self, chunk):
        ''' In this case, the metric count the number of bytes '''
        mbytes = (len(chunk)/1024.0)/1024
        self.register_metric(self.account,mbytes)
