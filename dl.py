from urllib.parse import unquote
import re
import json
import os
import requests
import threading
import time

#### Config options, change these ####
threads = 20
####


class Tracker:
    started = 0
    done = 0
    total = 0
    size = 0
    lock = threading.Lock()

    def set_started(self, val):
        with self.lock:
            self.started = val

    def set_done(self, val):
        with self.lock:
            self.done = val

    def set_total(self, val):
        with self.lock:
            self.total = val

    def set_size(self, val):
        with self.lock:
            self.size = val


tracker = Tracker()


def is_windows():
    return os.name == 'nt'


def title(text: str):
    if is_windows():
        os.system('title {}'.format(text.replace('|', '^|')))


def get_mod_url(project_id: int, file_id: int):
    return f'https://www.curseforge.com/api/v1/mods/{project_id}/files/{file_id}/download'


def get_mod_filename(url: str):
    # filename is the last portion of the url
    return unquote(url.split('/')[-1])


def dl_mod(url: str) -> int:  # returns downloaded size in bytes
    r = requests.get(url)
    if not r.ok:
        print('ERROR:' + r.text)
    filename = get_mod_filename(r.url)
    with open(f'mods/{filename}', 'wb') as file:
        file.write(r.content)

    return len(r.content)


def task(url: str):
    tracker.set_started(tracker.started + 1)
    print('Downloading: {}, {}/{} ({:0.2f}%)'.format(url,
                                                     tracker.started, tracker.total, tracker.started / tracker.total * 100))

    mod_size = dl_mod(url)
    tracker.set_size(tracker.size + mod_size)

    tracker.set_done(tracker.done + 1)


if not os.path.exists('mods'):
    os.mkdir('mods')


def update_task():
    while True:
        title('[CFDL] Done: {} | Total: {} | Progress: {:0.2f}% | Size: {:0.2f} MB | Active Threads: {}'.format(
            tracker.done, tracker.total, tracker.done / tracker.total * 100, tracker.size / 1000000, threading.active_count() - 2, threading.active_count()))
        time.sleep(.5)


def main():
    if not os.path.exists('manifest.json'):
        print('No manifest.json file found!')
        return

    with open('manifest.json', 'r') as modfile:
        data = json.load(modfile)
        files: list[str] = data['files']

        tracker.set_total(len(files))

        update_thread = threading.Thread(target=update_task)
        update_thread.daemon = True
        update_thread.start()

        started = time.time()

        while len(files) > 0:
            while threading.active_count() > threads:
                time.sleep(1)
            file = files.pop()
            url = get_mod_url(file['projectID'], file['fileID'])

            thread = threading.Thread(target=task, args=[url])
            thread.daemon = True
            thread.start()

        while threading.active_count() > 2:
            time.sleep(1)

        print('Done! Took {:0.2f}s and downloaded {:0.2f}MB'.format(
            time.time() - started, tracker.size / 1000000))


if __name__ == '__main__':
    main()
