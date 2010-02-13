
EMPTY_DB = {'_next': 1, 'x': {}}
DB = None

class Account(object):
  
  INDEXED_PROPS = ('x',)
  
  def __init__(self, **data):
    self.id = None
    self.x = 0
    self.y = 1
    self.model_only_prop = 555
    for k, v in data.iteritems():
      setattr(self, k, v)
      
  @staticmethod
  def find_by_x(x):
    return DB['x'].get(x, [])
    
  def delete(self):
    assert self.id is not None
    self.remove_from_index()
    del DB[self.id]
    self.id = None
    
  def add_to_index(self):
    for prop in self.INDEXED_PROPS:
      val = getattr(self, prop)
      DB[prop].setdefault(val, [])
      DB[prop][val].append(self)
    
  def remove_from_index(self):
    for prop in self.INDEXED_PROPS:
      val = getattr(self, prop)
      DB[prop].get(val, []).remove(self)
    
  def put(self):
    if self.id is None:
      self.id = DB['_next']
      self.key = '%s%d' % (self.__class__.__name__, self.id)
      DB['_next'] += 1
    old = DB.get(self.id)
    if old is not None:
      old.remove_from_index()
    DB[self.id] = self
    self.add_to_index()
