from eventlet import Timeout
import select
import os

CHUNK_SIZE = 64 * 1024

class AbstractMetric(object):
    def __init__(self, logger, crystal_control, metric_name, server, request, response):
        self.logger = logger
        self.request = request
        self.response = response
        self.crystal_control = crystal_control
        self.metric_name = metric_name
        self.current_server = server
        self.method = self.request.method
        self.storlet_executed = False
        
        self._parse_vaco()
        
    def register_metric(self, key, value):
        """
        Send data to publish thread
        """
        routing_key = self.metric_name
        self.crystal_control.publish_metric(routing_key, key, value)
        
    def _is_object_request(self):
        if self.current_server == 'proxy':
            path =  self.request.environ['PATH_INFO']
            if path.endswith('/'):
                path = path[:-1]
            splitted_path = path.split('/')
            if len(splitted_path)>4:   
                return True
        else:
            # TODO: Check for object-server
            return True

    def _get_object_reader(self):
        if self.method == 'GET' and self.current_server == 'proxy':
                reader = self.response.app_iter
        if self.method == 'GET' and self.current_server == 'object':
                reader = self.response.app_iter._fp
        if self.method == 'GET' and self.storlet_executed:
                reader = self.response.app_iter.obj_data
        if self.method == "PUT":
            reader = self.request.environ['wsgi.input']

        return reader
    
    def _intercept_request(self):
        reader = self._get_object_reader()
        if self.method == 'GET' and (self.storlet_executed or self.current_server == 'object'):
            self.response.app_iter = IterLikeFileDescriptor(reader, self, 10)
        if self.method == 'GET' and self.current_server == 'proxy':
            self.response.app_iter = IterLikeGetProxy(reader, self, 10)
        if self.method == 'PUT':
            self.request.environ['wsgi.input'] = IterLikePut(reader, self, 10)
        
    def _parse_vaco(self):
        if self._is_object_request():
            if self.current_server == 'proxy':  
                _, self.account, self.container, self.object = self.request.split_path(4, 4, rest_with_last=True)      
            else:
                _, _, self.account, self.container, self.object = self.request.split_path(5, 5, rest_with_last=True)
    
    def execute(self, request):
        """
        Execute Metric
        """
        raise NotImplementedError()



class IterLike(object):
    def __init__(self, obj_data, metric, timeout):
        self.closed = False
        self.obj_data = obj_data
        self.timeout = timeout
        self.metric = metric
        self.buf = b''

    def __iter__(self):
        return self

    def read_with_timeout(self, size):
        raise NotImplementedError()

    def next(self, size=CHUNK_SIZE):
        raise NotImplementedError()

    def _close_check(self):
        if self.closed:
            raise ValueError('I/O operation on closed file')

    def read(self, size=CHUNK_SIZE):
        self._close_check()
        return self.next(size)

    def readline(self, size=-1):
        self._close_check()

        # read data into self.buf if there is not enough data
        while b'\n' not in self.buf and \
              (size < 0 or len(self.buf) < size):
            if size < 0:
                chunk = self.read()
            else:
                chunk = self.read(size - len(self.buf))
            if not chunk:
                break
            self.buf += chunk

        # Retrieve one line from buf
        data, sep, rest = self.buf.partition(b'\n')
        data += sep
        self.buf = rest

        # cut out size from retrieved line
        if size >= 0 and len(data) > size:
            self.buf = data[size:] + self.buf
            data = data[:size]

        return data

    def readlines(self, sizehint=-1):
        self._close_check()
        lines = []
        try:
            while True:
                line = self.readline(sizehint)
                if not line:
                    break
                lines.append(line)
                if sizehint >= 0:
                    sizehint -= len(line)
                    if sizehint <= 0:
                        break
        except StopIteration:
            pass
        return lines

    def close(self):
        raise NotImplementedError()

    def __del__(self):
        self.close()

class IterLikePut(IterLike):

    def read_with_timeout(self, size):
        try:
            with Timeout(self.timeout):
                chunk = self.obj_data.read(size)
                self.metric.run_metric(chunk)
        except Timeout:
            self.close()
            raise
        except Exception:
            self.close()
            raise
        return chunk

    def next(self, size=CHUNK_SIZE):
        if len(self.buf) < size:
            self.buf += self.read_with_timeout(size - len(self.buf))
            if self.buf == b'':
                raise StopIteration('Stopped iterator ex')

        if len(self.buf) > size:
            data = self.buf[:size]
            self.buf = self.buf[size:]
        else:
            data = self.buf
            self.buf = b''
        return data

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.obj_data.close()

class IterLikeGetProxy(IterLike):

    def read_with_timeout(self, size):
        try:
            with Timeout(self.timeout):
                chunk = self.obj_data.next()
                self.metric.run_metric(chunk)
        except Timeout:
            self.close()
            raise
        except Exception:
            self.close()
            raise
        return chunk

    def next(self, size=CHUNK_SIZE):
        if len(self.buf) < size:
            self.buf += self.read_with_timeout(size - len(self.buf))
            if self.buf == b'':
                raise StopIteration('Stopped iterator ex')

        if len(self.buf) > size:
            data = self.buf[:size]
            self.buf = self.buf[size:]
        else:
            data = self.buf
            self.buf = b''
        return data

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.obj_data.close()

        
class IterLikeFileDescriptor(IterLike):
    def __init__(self, obj_data, metric, timeout):        
        IterLike.__init__(obj_data, metric, timeout)

        self.epoll = select.epoll()
        self.epoll.register(self.obj_data, select.EPOLLIN | select.EPOLLPRI)

    def __iter__(self):
        return self

    def read_with_timeout(self, size):
        try:
            with Timeout(self.timeout):
                chunk = os.read(self.obj_data, size) 
                self.metric.run_metric(chunk)
        except Timeout:
            self.close()
            raise
        except Exception:
            self.close()
            raise
        return chunk

    def next(self, size=CHUNK_SIZE):
        if len(self.buf) < size:
            r = self.epoll.poll(self.timeout)

            if len(r) == 0:
                self.close()
            elif self.obj_data in r[0]:
                self.buf += self.read_with_timeout(size - len(self.buf))
                if self.buf == b'':
                    raise StopIteration('Stopped iterator ex')
            else:
                raise StopIteration('Stopped iterator ex')

        if len(self.buf) > size:
            data = self.buf[:size]
            self.buf = self.buf[size:]
        else:
            data = self.buf
            self.buf = b''
        return data

    def close(self):
        if self.closed:
            return
        self.closed = True
        
        self.epoll.unregister(self.obj_data)
        self.epoll.close()
        os.close(self.obj_data)
