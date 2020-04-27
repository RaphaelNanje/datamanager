import gc
import logging
import os
from collections import UserDict
from random import randint
from typing import (Sized, Iterable, Dict, Union, Mapping)

from diskcache import Index, Deque
from easyfilemanager import FileManager

from datamanager.cachetypes import CacheSet, EvictingIndex
from datamanager.save_daemon import SaveDaemon


def _numericize(loaded_data):
    """
    If a number can be turned into a number, turn it into a number
    This avoids duplicates such as 1 and "1"
    """
    new_iterable = []
    for i in loaded_data:
        var = i
        try:
            var = int(i)
        except (ValueError, TypeError):
            pass
        finally:
            new_iterable.append(var)
    return new_iterable


class DataManager(UserDict):
    filemanager = FileManager()
    directory = '.'
    do_not_display = []  # data items not to show in StatDisplay
    do_not_save = []
    do_not_append_session_id = []
    save_kwargs: 'Dict[str, Dict]' = {}
    load_kwargs: 'Dict[str, Dict]' = {}

    def __init__(self, *args, **kwargs: dict) -> None:
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(type(self).__name__)
        self.session_id = str(randint(100000, 999999))
        self.save_daemon = SaveDaemon()
        self.save_daemon.funcs.extend((self.save, self.save_caches))

    def register(self, name, data, display=False, append_session_id=True):
        """"""
        if append_session_id:
            name = name + self.session_id
        else:
            self.do_not_append_session_id.append(name + self.session_id)
        if not display:
            self.do_not_display.append(name)
        self[name] = data

    def register_file(self, name, initial_data: Union[set, list, Mapping],
                      path_to_file=directory, display=True, load=True,
                      save=True,
                      save_kwargs: dict = None, load_kwargs: dict = None):
        """
        Register and load a data file.
        """
        if isinstance(initial_data, type):
            raise TypeError(
                'initial_data argument must be an object, not type')
        self.logger.debug('registering "%s" -> "%s"', name, path_to_file)
        if not display:
            self.do_not_display.append(name)
        if not save:
            self.do_not_save.append(name)
        if save_kwargs:
            self.save_kwargs[name] = save_kwargs
        if load_kwargs:
            self.load_kwargs[name] = load_kwargs
        else:
            load_kwargs = {}
        loaded_data = None
        file_path, file_name = os.path.split(path_to_file)
        if not file_path:
            file_path = '.'
        _, file_type = os.path.splitext(file_name)
        self.filemanager.register_file(file_name, file_path, short_name=name)
        if load and self.filemanager.exists(name):
            loaded_data = self.filemanager.smart_load(name, **load_kwargs)
            self.logger.debug('loaded data for "%s" -> %s', name,
                              (str(loaded_data)[:75] + '...') if len(
                                  str(loaded_data)) > 75 else str(
                                  loaded_data))
        self.register(name, initial_data, display, append_session_id=False)
        if loaded_data:
            self.load(initial_data, loaded_data, name)

    def register_cache(self, name, initial_data: Union[set, list, Mapping],
                       path_to_file=None, display=True, load=True, save=True,
                       save_kwargs: dict = None, load_kwargs: dict = None,
                       directory='.', append_session_id=True) -> None:
        """
        The purpose of this function is to avoid having all objects loaded
        in memory and instead use a diskcache for storing/accessing objects.

        This function will create a cache at './cache/**name**' and register
        the file passed to `path_to_file` for auto-saving.

        If `path_to_file` is None, then data will only be saved to the cache

        This data will be accessed by `JobManager.context.data.get(name)` and
        will return one of the following: :class:`Index`, :class:`CacheSet`,
        or :class:`Deque`.

        This data will be saved using ``save()``
        Args:
            directory: The name of the folder in ./cache/ to save this cache to
            name: The name to access this cache by `self.get(name)`
            initial_data: The kind of cache to save data to (set, list, dict)
            path_to_file: An optional file to save cached data to on exit
            display: Whether to show this in the StatDisplay
            load:  Whether to load existing data in `path_to_file `into the cache
            save: Whether to auto save data
            save_kwargs: Kwargs to pass when saving via `FileManager`
            load_kwargs: Kwargs to pass when loading via `FileManager`
            append_session_id: Add the session_id to the name variable
        Returns:

        """
        if isinstance(initial_data, type):
            raise TypeError(
                'initial_data argument must be an object, not type')
        if append_session_id:
            name = name + self.session_id
        else:
            self.do_not_append_session_id.append(name + self.session_id)
        self.logger.debug('registering "%s" -> "%s"', name, path_to_file)
        if not display: self.do_not_display.append(name)
        if not save: self.do_not_save.append(name)
        if save_kwargs: self.save_kwargs[name] = save_kwargs
        if load_kwargs: self.load_kwargs[name] = load_kwargs
        else: load_kwargs = {}
        loaded_data = None
        if path_to_file:
            file_path, file_name = os.path.split(path_to_file)
            if not file_path: file_path = '.'
            self.filemanager.register_file(file_name, file_path,
                                           short_name=name)

            if load and self.filemanager.exists(name):
                loaded_data = self.filemanager.smart_load(name, **load_kwargs)
                self.logger.debug('loaded data for "%s" -> %s', name,
                                  (str(loaded_data)[:75] + '...') if len(
                                      str(loaded_data)) > 75 else str(
                                      loaded_data))
            else:
                loaded_data = initial_data
        self._create_cache(initial_data, loaded_data, name, directory)
        del loaded_data
        gc.collect()

    def _create_cache(self, initial_data, loaded_data, name, directory):
        if '/' in name:
            path_name = name.split('/')[1]
        else: path_name = name
        path = os.path.join('cache', directory, path_name)
        if isinstance(initial_data, set):
            if loaded_data: loaded_data = _numericize(loaded_data)
            self[name] = CacheSet(loaded_data or set(), path)
            self.logger.debug('creating new CacheSet for %s', name)
        elif isinstance(initial_data, list):
            self[name] = Deque(loaded_data or [], path)
            self.logger.debug('creating new Deque for %s', name)
        elif isinstance(initial_data, dict):
            self[name] = EvictingIndex(path, **(loaded_data or {}))
            self.logger.debug('creating new Index for %s', name)

    def load(self, data, loaded_data, name):
        if isinstance(loaded_data, Iterable) and not isinstance(
            loaded_data, dict):
            new_iterable = _numericize(loaded_data)
            loaded_data = new_iterable
        if isinstance(data, set):
            self[name].update(loaded_data)
        elif isinstance(data, list):
            self[name].extend(loaded_data)
        elif isinstance(data, dict):
            self[name].update(loaded_data)

    def get(self, k, optional=None) -> Union[list, dict, set]:
        k = k + self.session_id
        if k in self.do_not_append_session_id:
            k = k.replace(self.session_id, '')
        return super().get(k, optional)

    def file_update(self, name, data):
        self[name] = data

    def get_data_string(self) -> str:
        string = ''
        string += f'\n\t\t    <{"TOTALS".center(55, "-")}>\n'
        for k, v in self.items():
            if k in self.do_not_display:
                continue
            # only print the length of iterable values
            if isinstance(v, Sized) and not isinstance(v, (str, bytes)):
                string += f'\t\t\t    {k}: {len(v)}\n'
        string += f'\t\t    <{"END TOTALS".center(55, "-")}>\n'
        return string.rstrip()

    def save(self):
        for name, value in self.items():
            # check if this key has a file name
            if name not in self.filemanager or name in self.do_not_save:
                continue
            # if value is empty continue
            if not value:
                continue
            save_kwargs = self.save_kwargs.get(name, {})
            try:
                self.filemanager.smart_save(name, value,
                                            **save_kwargs)
            except Exception as e:
                self.logger.exception(e)

    def save_caches(self):
        self.logger.debug('saving cache files')
        for name, value in self.items():
            save_kwargs = self.save_kwargs.get(name, {})
            if name not in self.filemanager or name in self.do_not_save:
                continue
            if isinstance(value, (CacheSet, Deque)):
                self.filemanager.smart_save(name, list(value), mode='w+',
                                            **save_kwargs)
            elif isinstance(value, (Index, EvictingIndex)):
                self.filemanager.smart_save(name, dict(value),
                                            **save_kwargs)

    def clean(self):
        """
        Save storage space by clearing the caches when the data
        is already stored as a file
        """
        for name, value in self.items():
            if name not in self.filemanager:
                continue
            if isinstance(value, (CacheSet, Deque, Index)):
                value.clear()
                import shutil
                shutil.rmtree(value.directory)

    def start_save_daemon(self, sleep_time: int = None):
        if sleep_time:
            self.save_daemon.sleep = sleep_time
        self.save_daemon.start()

    def stop_daemon(self):
        self.save_daemon.go = False
