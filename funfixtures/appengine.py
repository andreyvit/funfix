
from funfixtures.common import AbstractFixture

class AppEngineFixture(AbstractFixture):

  @classmethod
  def get_primary_key(fix_klass, item_klass, item_instance):
    return item_instance.key()
  
  @classmethod
  def create_item_instance(fix_klass, item_klass, values):
    result = fix_klass.Entity(**values)
    result.put()
    return result
    
  @classmethod
  def destroy_item_instance(fix_klass, item_klass, item_instance):
    item_instance.delete()
