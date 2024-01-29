import inspect
import os, sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .reload import reload


class FileModifiedHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.event_type == 'modified' and not event.is_directory and os.path.splitext(event.src_path)[1] == '.py':
            file_path = event.src_path
            try:
                module_name = '.'.join(os.path.relpath(file_path, path).split('\\'))[:-3]
                if sys.modules.get(module_name):
                    reload(sys.modules.get(module_name))
            except Exception as e:
                print("Exception",e)
def start_watcher(directory_to_watch):
    event_handler = FileModifiedHandler()
    global path 
    path = '\\'.join(directory_to_watch.split('\\')[:-1])
    observer = Observer()
    observer.schedule(event_handler, directory_to_watch, recursive=True)
    observer.start()
    return observer 
