
from google.appengine.ext import db
from funfixtures.common import AbstractFixture, FixtureError

def compute_key_name_func_arg(arg_name, values, fixture_name, func_name):
  if arg_name in values:
    return values[arg_name]
  elif arg_name.endswith('_key'):
    arg_name = arg_name[:-4]
    v = values[arg_name]
    if isinstance(v, db.Model):
      v = v.key()
    assert (v is None) or isinstance(v, db.Key)
    return v
  elif arg_name.endswith('_key_name'):
    key_name = arg_name[:-9]
    v = values[key_name]
    if v is not None:
      if isinstance(v, db.Model):
        v = v.key()
        if v is None:
          raise FixtureError, "Error computing argument '%s' when autogenerating key name via %s: '%s.%s' is an unsaved entity without a key" % (arg_name, func_name, fixture_name, key_name)
        v = v.id_or_name()
      elif isinstance(v, db.Key):
        v = v.id_or_name()
      else:
        if not isinstance(v, (basestring, int, long)):
          raise FixtureError, "Error computing argument '%s' when autogenerating key name via %s: '%s.%s' is not a string, int or long (is %s instead)" % (arg_name, func_name, fixture_name, key_name, type(v))
    return v
  else:
    raise FixtureError, "Error computing argument '%s' when autogenerating key name via %s for fixture %s: no matching attribute found (tried '%s', '%s_key' and '%s_key_name')" % (arg_name, func_name, fixture_name, arg_name, arg_name, arg_name)

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
        args = dict([(arg_name, compute_key_name_func_arg(arg_name, values, fixture_name, '%s.%s' % (Entity.__name__, 'key_name_for'))) for arg_name in arg_names])
        key_name = func(**args)
        assert isinstance(key_name, basestring)
        values['key_name'] = key_name
      elif hasattr(Entity, 'key_for'):
        func = Entity.key_for
        arg_names = func.func_code.co_varnames[0:func.func_code.co_argcount]
        args = dict([(arg_name, compute_key_name_func_arg(arg_name, values, fixture_name, '%s.%s' % (Entity.__name__, 'key_for'))) for arg_name in arg_names])
        key = func(**args)
        assert isinstance(key, db.Key)
        values['key_name'] = key.name()

    result = Entity(**values)
    result.put()
    
    for k in values:
      if not hasattr(result, k):
        if not k in ('key', 'parent', 'key_name'):
          setattr(result, k, values[k])
        
    return result
    
  @classmethod
  def destroy_item_instance(fix_klass, item_klass, item_instance):
    item_instance.delete()
