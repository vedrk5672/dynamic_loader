import types
from datetime import datetime

def execfile(file, glob=None, loc=None):
    if glob is None:
        import sys
        glob = sys._getframe().f_back.f_globals
    if loc is None:
        loc = glob
    import tokenize
    with tokenize.open(file) as stream:
        contents = stream.read()
    exec(compile(contents + "\n", file, 'exec'), glob, loc)

def code_objects_equal(code0, code1):
    for d in dir(code0):
        if d.startswith('_') or 'line' in d or d in ('replace', 'co_positions', 'co_qualname'):
            continue
        if getattr(code0, d) != getattr(code1, d):
            return False
    return True


LEVEL1 = 1
LEVEL2 = 2
DEBUG = 0
global counter
counter = 0

def write_err(*args):
    print(f"{datetime.now().strftime('[%d/%m/%y %H:%M:%S]')} code reload {' '.join([str(a) for a in args])}")

def notify_info0(*args):
    write_err(*args)

def notify_info(*args):
    if DEBUG >= LEVEL1:
        write_err(*args)

def notify_info2(*args):
    if DEBUG >= LEVEL2:
        write_err(*args)

def notify_error(*args):
    write_err(*args)

def reload(mod):
    r = Reload(mod)
    r.apply()
    found_change = r.found_change
    r = None
    return found_change


class Reload:

    def __init__(self, mod, mod_name=None, mod_filename=None):
        self.mod = mod
        if mod_name:
            self.mod_name = mod_name
        else:
            self.mod_name = mod.__name__ if mod is not None else None
        if mod_filename:
            self.mod_filename = mod_filename
        else:
            self.mod_filename = mod.__file__ if mod is not None else None
        self.found_change = False

    def apply(self):
        mod = self.mod
        self._on_finish_callbacks = []
        try:
            modns = mod.__dict__
            new_namespace = modns.copy()
            new_namespace.clear()
            if self.mod_filename:
                new_namespace["__file__"] = self.mod_filename
                try:
                    new_namespace["__builtins__"] = __builtins__
                except NameError:
                    raise  
            if self.mod_name:
                new_namespace["__name__"] = self.mod_name
                if new_namespace["__name__"] == '__main__':
                    new_namespace["__name__"] = '__main_reloaded__'
            execfile(self.mod_filename, new_namespace, new_namespace)
            oldnames = set(modns)
            newnames = set(new_namespace)
            for name in newnames - oldnames:
                self.found_change = True
                modns[name] = new_namespace[name]
            for name in oldnames & newnames:
                self._update(modns, name, modns[name], new_namespace[name])
            self._handle_namespace(modns)
            for c in self._on_finish_callbacks:
                c()
            del self._on_finish_callbacks[:]
        except Exception as e:
            print(f"Error : {e}")
    
    def _handle_namespace(self, namespace, is_class_namespace=False):
        on_finish = None
        if is_class_namespace:
            xreload_after_update = getattr(namespace, '__xreload_after_reload_update__', None)
            if xreload_after_update is not None:
                self.found_change = True
                on_finish = lambda: xreload_after_update()
        elif '__xreload_after_reload_update__' in namespace:
            xreload_after_update = namespace['__xreload_after_reload_update__']
            self.found_change = True
            on_finish = lambda: xreload_after_update(namespace)
        if on_finish is not None:
            self._on_finish_callbacks.append(on_finish)
    
    def _update(self, namespace, name, oldobj, newobj, is_class_namespace=False):
        try:
            notify_info2('Updating: ', oldobj)
            if oldobj is newobj:
                return
            if type(oldobj) is not type(newobj):
                if name not in ('__builtins__',):
                    notify_error('Type of: %s (old: %s != new: %s) changed... Skipping.' % (name, type(oldobj), type(newobj)))
                return
            if isinstance(newobj, types.FunctionType):
                self._update_function(oldobj, newobj)
                return
            if isinstance(newobj, types.MethodType):
                self._update_method(oldobj, newobj)
                return
            if isinstance(newobj, classmethod):
                self._update_classmethod(oldobj, newobj)
                return
            if isinstance(newobj, staticmethod):
                self._update_staticmethod(oldobj, newobj)
                return
            if hasattr(types, 'ClassType'):
                classtype = (types.ClassType, type)  
            else:
                classtype = type
            if isinstance(newobj, classtype):
                self._update_class(oldobj, newobj)
                return
            if hasattr(newobj, '__metaclass__') and hasattr(newobj, '__class__') and newobj.__metaclass__ == newobj.__class__:
                self._update_class(oldobj, newobj)
                return
            if namespace is not None:
                xreload_old_new = None
                if is_class_namespace:
                    xreload_old_new = getattr(namespace, '__xreload_old_new__', None)
                    if xreload_old_new is not None:
                        self.found_change = True
                        xreload_old_new(name, oldobj, newobj)
                elif '__xreload_old_new__' in namespace:
                    xreload_old_new = namespace['__xreload_old_new__']
                    xreload_old_new(namespace, name, oldobj, newobj)
                    self.found_change = True
        except:
            notify_error('Exception found when updating %s. Proceeding for other items.' % (name,))
    
    def _update_function(self, oldfunc, newfunc):
        oldfunc.__doc__ = newfunc.__doc__
        oldfunc.__dict__.update(newfunc.__dict__)
        try:
            newfunc.__code__
            attr_name = '__code__'
        except AttributeError:
            newfunc.func_code
            attr_name = 'func_code'
        old_code = getattr(oldfunc, attr_name)
        new_code = getattr(newfunc, attr_name)
        if not code_objects_equal(old_code, new_code):
            notify_info0('Updated function code:', oldfunc)
            setattr(oldfunc, attr_name, new_code)
            self.found_change = True
        try:
            oldfunc.__defaults__ = newfunc.__defaults__
        except AttributeError:
            oldfunc.func_defaults = newfunc.func_defaults
        return oldfunc
    
    def _update_method(self, oldmeth, newmeth):
        if hasattr(oldmeth, 'im_func') and hasattr(newmeth, 'im_func'):
            self._update(None, None, oldmeth.im_func, newmeth.im_func)
        elif hasattr(oldmeth, '__func__') and hasattr(newmeth, '__func__'):
            self._update(None, None, oldmeth.__func__, newmeth.__func__)
        return oldmeth
    
    def _update_class(self, oldclass, newclass):
        olddict = oldclass.__dict__
        newdict = newclass.__dict__
        oldnames = set(olddict)
        newnames = set(newdict)
        for name in newnames - oldnames:
            setattr(oldclass, name, newdict[name])
            notify_info0('Added:', name, 'to', oldclass)
            self.found_change = True
        for name in (oldnames & newnames) - set(['__dict__', '__doc__']):
            self._update(oldclass, name, olddict[name], newdict[name], is_class_namespace=True)
        old_bases = getattr(oldclass, '__bases__', None)
        new_bases = getattr(newclass, '__bases__', None)
        if str(old_bases) != str(new_bases):
            notify_error('Changing the hierarchy of a class is not supported. %s may be inconsistent.' % (oldclass,))
        self._handle_namespace(oldclass, is_class_namespace=True)
    
    def _update_classmethod(self, oldcm, newcm):
        self._update(None, None, oldcm.__get__(0), newcm.__get__(0))
    
    def _update_staticmethod(self, oldsm, newsm):
        self._update(None, None, oldsm.__get__(0), newsm.__get__(0))
