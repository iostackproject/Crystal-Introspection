from setuptools import setup

paste_factory = ['crystal_introspection_handler = '
                 'crystal_introspection_middleware.crystal_introspection_handler:filter_factory']

setup(name='swift_crystal_introspection_middleware',
      version='0.0.1',
      description='Crystal Introspection middleware for OpenStack Swift',
      author='The AST-IOStack Team: Josep Sampe, Raul Gracia',
      url='http://iostack.eu',
      packages=['crystal_introspection_middleware'],
      requires=['swift(>=1.4)'],
      entry_points={'paste.filter_factory':paste_factory}
      )
