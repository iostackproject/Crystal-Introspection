This repository has moved to<br />https://github.com/Crystal-SDS/introspection-middleware
=========================================================================================

Crystal Introspection Middleware for OpenStack Swift
====================================================

## Installation

To install the module you can run the next line in the parent folder:
```python
python setup.py install
```

After that, it is necessary to configure OpenStack Swift to add the middleware in the proxy and the object servers.

- We need to add a new filter that must be called crystal_introspection_handler in the ( `proxy-server.conf`): you can copying the next lines in the bellow part of the file:
```
[filter:crystal_introspection_handler]
use = egg:swift_crystal_introspection_middleware#crystal_introspection_handler
execution_server = proxy
```
- We need to add a new filter that must be called swift_sds in the ( `object-server.conf`): you can copying the next lines in the bellow part of the file:
```
[filter:crystal_introspection_handler]
use = egg:swift_crystal_introspection_middleware#crystal_introspection_handler
execution_server = object
```
- Also it is necessary to add this filter in the pipeline variable. This filter must be
added before `storlet_handler` filter.

- The last step is restart the proxy-server service. Now the middleware has been installed.
