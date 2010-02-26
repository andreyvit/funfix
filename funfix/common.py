
__all__ = ('AbstractFixture',)

from types import ClassType
import functools

LOG = False


def compute_mro(klass):
  if hasattr(klass, '__mro__'): return klass.__mro__
  result = [klass,]
  for b in klass.__bases__: result += compute_mro(b)
  return result
  
class FixtureError(Exception):
  pass
  
class PleaseLoadItem(Exception):
  
  def __init__(self, item_klass, cause, attr):
    self.item_klass = item_klass
    self.cause = cause
    self.attr = attr
  

def FixtureItem_getattr(item_klass, attr):
  if FixtureMeta.loading_counter == 0:
    return getattr(item_klass.__class__, attr)
  else:
    try:
      return getattr(item_klass.__class__, attr)
    except AttributeError, e:
      raise PleaseLoadItem(item_klass, e, attr)
      
class DependsOnFutureKey(Exception):
  def __init__(self, key):
    self.key = key
    
class ItemKlassLoadingProxy(object):
  def __init__(self, obj, values):
    self.obj = obj
    self.values = values
    self.disallowed_keys = []
  
  def __getattr__(self, key):
    if key in self.disallowed_keys:
      raise DependsOnFutureKey(key)
    if key in self.values:
      return self.values[key]
    return getattr(self.obj, key)
    
class FixtureMeta(type):
  
  PRIMARY_KEY_NAME = 'id'
  loading_counter = 0
  
  def __new__(cls, name, bases, members):
    bases = list(bases)
    
    if name != 'AbstractFixture':
      # need AbstractFixture to be already defined to reference it in the code below
      
      entity_klass = members.get('Entity', None)
      if entity_klass is None:
        for base in bases:
          if not issubclass(base, AbstractFixture):
            entity_klass = base
            bases.remove(entity_klass)
            break
          
        if entity_klass is None:
          for base in bases:
            if hasattr(base, 'Entity'):
              entity_klass = base.Entity
              break
        
        if entity_klass is not None:
          members['Entity'] = entity_klass
    else:
      entity_klass = None
    
    item_klasses = {}
    for k, v in members.items():
      if k.startswith('_') or (entity_klass is not None and v == entity_klass): continue
      if isinstance(v, (ClassType, type)):
        assert v.__name__ == k, "Naming problem: expected '%s', got '%s'" % (k, v.__name__)
        
        v.__getattr__ = FixtureItem_getattr
        item_klass = v()
        item_klass.__name__ = k
        item_klasses[k] = item_klass
        members[k] = item_klass
        
    members['_item_klasses'] = item_klasses
      
    fix_klass = type.__new__(cls, name, tuple(bases), members)
    
    for item_klass in item_klasses.values():
      values, deps = {}, {}
      
      for klass in reversed(compute_mro(item_klass.__class__)):
        for k, v in klass.__dict__.iteritems():
          if k.startswith('_'): continue
        
          if hasattr(v, '_fixture'):
            def get_primary_key(self, kl=v):
              if kl._load_count == 0: raise PleaseLoadItem(kl, None, 'key')
              return kl._fixture.get_primary_key(kl, kl._instance)
            v = get_primary_key
          if hasattr(v, '__call__'):
            deps[k] = v
          else:
            values[k] = v
      
      item_klass._values, item_klass._deps = values, deps
      item_klass._fixture = fix_klass
      item_klass._load_count = 0
      
    return fix_klass
  
  
  # mass loading/unloading
  
  def _load_self(fix_klass):
    for name, item_klass in fix_klass._item_klasses.items():
      fix_klass.load_item(item_klass)
    
  def _unload_self(fix_klass):
    for name, item_klass in fix_klass._item_klasses.items():
      fix_klass.unload_item(item_klass)
    
  def load(fix_klass):
    for base in reversed(fix_klass.__mro__):
      if hasattr(base, '_load_self'):
        base._load_self()
    
  def unload(fix_klass):
    for base in fix_klass.__mro__:
      if hasattr(base, '_unload_self'):
        base._unload_self()
  
     
  # single item loading/unloading
      
  def load_item(fix_klass, item_klass):
    if LOG: print "load_item(%s.%s)" % (fix_klass.__name__, item_klass.__name__)
    assert item_klass._fixture is fix_klass
    
    if item_klass._load_count > 1:
      if not hasattr(item_klass, '_instance'):
        raise FixtureError, 'Internal error: did not clean up properly after a failed loading attemp of %s.%s' % (fix_klass.__name__, item_klass.__name__)
      return item_klass._instance
      
    values = item_klass._values.copy()
    item_klass._items_to_unload = []
    loaded_this_time = []
    deps_this_time = item_klass._deps
    
    # helps detect lambda attributes that depend on other not-yet-calculated lambda attributes
    proxy = ItemKlassLoadingProxy(item_klass, values)
    
    # attributes defined as lambdas may depend on each other, so resolve them iteratively
    while len(deps_this_time) > 0:
      deps_next_time = {}
      proxy.disallowed_keys = deps_this_time.keys()
      processed_deps = 0
      for k, v in deps_this_time.iteritems():
        # retry if external dependency loading has been triggered
        while True:
          try:
            FixtureMeta.loading_counter += 1
            try:
              if LOG: print ".. loading %s.%s.%s" % (fix_klass.__name__, item_klass.__name__, k)
              if v.func_code.co_argcount >= 1:
                values[k] = v(proxy)
              else:
                values[k] = v()
            finally:
              FixtureMeta.loading_counter -= 1
            processed_deps += 1
            if LOG: print ".. .. done"
            break
          except DependsOnFutureKey, e:
            deps_next_time[k] = v
            if LOG: print ".. .. depends on self.%s" % e.key
            break
          except PleaseLoadItem, e:
            if LOG: print ".. .. depends on %s.%s.%s" % (e.item_klass._fixture.__name__, e.item_klass.__name__, e.attr)
            if e.item_klass == item_klass:
              raise StandardError, "Please don't use '%(f)s.%(i)s.%(a)s' to access the current fixture in %(k)s; instead, accept 'self' arguments and use 'self.%(a)s'" % dict(f=fix_klass.__name__, i=item_klass.__name__, k=k, a=e.attr)
            if e.item_klass in loaded_this_time:
              raise e.cause
            else:
              item_klass._items_to_unload.append(e.item_klass)
              e.item_klass._fixture.load_item(e.item_klass)
              loaded_this_time.append(e.item_klass)
      if processed_deps == 0:
        raise StandardError, "Circular dependency between attributes of %s.%s" % (fix_klass.__name__, item_klass.__name__)
      deps_this_time = deps_next_time
      
    item_instance = fix_klass.create_item_instance(item_klass, values)
    assert item_instance is not None, "create_item_instance(%s.%s) returned None" % (fix_klass.__name__, item_klass.__name__)
    
    item_klass._load_count += 1
    item_klass._instance = item_instance
    setattr(fix_klass, item_klass.__name__, item_instance)
    if LOG: print "DONE %s.%s" % (fix_klass.__name__, item_klass.__name__)
    return item_klass._instance
      
  def unload_item(fix_klass, item_klass):
    assert item_klass._fixture is fix_klass
    
    assert item_klass._load_count > 0, "Too many attemps to unload %s.%s" % (fix_klass.__name__, item_klass.__name__)
    item_klass._load_count -= 1
    if item_klass._load_count > 0: return
    
    assert item_klass._instance is not None, "Attemp to unload a fixture item that has not been loaded: %s.%s" % (fix_klass.__name__, item_klass.__name__)
    fix_klass.destroy_item_instance(item_klass, item_klass._instance)
    item_klass._instance = None
    setattr(fix_klass, item_klass.__name__, item_klass)
    
    for ik in item_klass._items_to_unload:
      ik._fixture.unload_item(ik)
    item_klass._items_to_unload = None

    
    
  # decoration
    
  def __call__(fix_klass, f):
    @functools.wraps(f)
    def decorated(*args, **kw):
      fix_klass.load()
      try:
        f(*args, **kw)
      finally:
        fix_klass.unload()
    return decorated
  

class AbstractFixture(object):
  
  __metaclass__ = FixtureMeta
  
  @classmethod
  def create_item_instance(fix_klass, item_klass, values):
    raise NotImplementedError, "Please derive from an ancestor of AbstractFixture that defines create_item_instance and destroy_item_instance"
    
  @classmethod
  def destroy_item_instance(fix_klass, item_klass, item_instance):
    raise NotImplementedError, "Please derive from an ancestor of AbstractFixture that defines create_item_instance and destroy_item_instance"

  @classmethod
  def get_primary_key(fix_klass, item_klass, item_instance):
    return item_instance.id
