from crystal_introspection_thread import CrystalIntrospectionControl
from swift.common.swob import HTTPInternalServerError
from swift.common.swob import HTTPException
from swift.common.swob import wsgify
from swift.common.utils import get_logger


class CrystalIntrospectionHandler():

    def __init__(self, request, conf, app, logger, crystal_control):
        self.exec_server = conf.get('execution_server')
        self.request = request
        self.crystal_control = crystal_control

    def handle_request(self):
        self.metrics = self.crystal_control.get_metrics()
        
        return self.request.get_response(self.app)

class CrystalIntrospectionHandlerMiddleware(object):

    def __init__(self, app, conf, crystal_conf):
        self.app = app
        self.logger = get_logger(conf, log_route='sds_storlet_handler')
        self.introspection_conf = crystal_conf
        
        self.handler_class = CrystalIntrospectionHandler
        
        ''' Singleton instance of Introspection control '''
        self.crystal_control = CrystalIntrospectionControl.Instance(conf = crystal_conf,
                                                                    logger = self.logger)
        
    @wsgify
    def __call__(self, req):
        try:
            request_handler = self.handler_class(
                req, self.introspection_conf, self.app, self.logger, self.crystal_control)
            self.logger.debug('crystal_introspection_handler call in %s: with %s/%s/%s' %
                              (self.exec_server, request_handler.account,
                               request_handler.container,
                               request_handler.obj))
        except:
            return req.get_response(self.app)

        try:
            return request_handler.handle_request()
        except HTTPException:
            self.logger.exception('Crystal Introspection execution failed')
            raise
        except Exception:
            self.logger.exception('Crystal Introspection execution failed')
            raise HTTPInternalServerError(body='Crystal Introspection execution failed')


def filter_factory(global_conf, **local_conf):
    """Standard filter factory to use the middleware with paste.deploy"""
    
    conf = global_conf.copy()
    conf.update(local_conf)

    crystal_conf = dict()
    crystal_conf['execution_server'] = conf.get('execution_server', 'object')
    
    crystal_conf['rabbit_host'] = conf.get('rabbit_host', 'controller')
    crystal_conf['rabbit_port'] = conf.get('rabbit_port', 5672)
    crystal_conf['rabbit_username'] = conf.get('rabbit_username', 'openstack')
    crystal_conf['rabbit_password'] = conf.get('rabbit_password', 
                                               'rabbitmqastl1a4b4')

    crystal_conf['redis_host'] = conf.get('redis_host', 'controller')
    crystal_conf['redis_port'] = conf.get('redis_port', 6379)
    crystal_conf['redis_db'] = conf.get('redis_db', 0)


    def swift_crystal_introspection_middleware(app):
        return CrystalIntrospectionHandlerMiddleware(app, conf, crystal_conf)

    return swift_crystal_introspection_middleware
