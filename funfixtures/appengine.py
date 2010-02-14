
from google.appengine.ext import db
from funfixtures.common import AbstractFixture

def compute_key_name_func_arg(arg_name, values, fixture_name):
  if arg_name in values:
    return values[arg_name]
  elif arg_name.endswith('_key'):
    arg_name = arg_name[:-4]
    v = values[arg_name]
    assert (v is None) or isinstance(v, db.Key)
    return v
  elif arg_name.endswith('_key_name'):
    arg_name = arg_name[:-9]
    v = values[arg_name]
    if v is not None:
      if isinstance(v, db.Key):
        v = v.name()
      assert isinstance(v, basestring)
    return v
  else:
    raise KeyError, "Error calling key generator function: cannot populate argument '%s' for %s" % (arg_name, fixture_name)

class AppEngineFixture(AbstractFixture):

  @classmethod
  def get_primary_key(fix_klass, item_klass, item_instance):
    return item_instance.key()
  
  @classmethod
  def create_item_instance(fix_klass, item_klass, values):
    values = dict(values)
    Entity = fix_klass.Entity
    if 'key_name' not in values:
      fixture_name = '%s.%s' % (fix_klass.__name__, item_klass.__name__)
      if hasattr(Entity, 'key_name_for'):
        func = Entity.key_name_for
        arg_names = func.func_code.co_varnames[0:func.func_code.co_argcount]
        args = dict([(arg_name, compute_key_name_func_arg(arg_name, values, fixture_name)) for arg_name in arg_names])
        key_name = func(**args)
        assert isinstance(key_name, basestring)
        values['key_name'] = key_name
      elif hasattr(Entity, 'key_for'):
        func = Entity.key_for
        arg_names = func.func_code.co_varnames[0:func.func_code.co_argcount]
        args = dict([(arg_name, compute_key_name_func_arg(arg_name, values, fixture_name)) for arg_name in arg_names])
        key = func(**args)
        assert isinstance(key, db.Key)
        values['key_name'] = key.name()

    result = Entity(**values)
    result.put()
    return result
    
  @classmethod
  def destroy_item_instance(fix_klass, item_klass, item_instance):
    item_instance.delete()
