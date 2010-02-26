
__all__ = ('SampleDbFixture', 'with_empty_db')

from funfix import AbstractFixture
import sampledb
import functools

class SampleDbFixture(AbstractFixture):
  
  @classmethod
  def create_item_instance(fix_klass, item_klass, values):
    result = fix_klass.Entity(**values)
    result.put()
    return result
    
  @classmethod
  def destroy_item_instance(fix_klass, item_klass, item_instance):
    item_instance.delete()


def with_empty_db(func):
  @functools.wraps(func)
  def decorated():
    sampledb.DB = sampledb.EMPTY_DB.copy()
    func()
    db = sampledb.DB
    sampledb.DB = None
    assert len(sampledb.EMPTY_DB) == 2
    assert len(db) == len(sampledb.EMPTY_DB), "%d extra item(s) in DB after execution of %s" % (len(db) - len(sampledb.EMPTY_DB), func.__name__)
  return decorated
