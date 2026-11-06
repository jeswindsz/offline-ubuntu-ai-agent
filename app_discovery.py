import configparser
import os
import re
import shutil
import subprocess
from pathlib import Path

SEARCH_DIRS = [Path.home()/'.local/share/applications', Path('/usr/local/share/applications'), Path('/usr/share/applications')]
SEARCH_DIRS += [Path(p)/'applications' for p in os.environ.get('XDG_DATA_DIRS','').split(':') if p]

GROUPS = {
 'browser': {'terms': ('browser','web browser','internet'), 'categories': ('WebBrowser',), 'names': ('brave','chrome','chromium','firefox','vivaldi','opera','edge')},
 'editor': {'terms': ('text editor','code editor','editor','ide'), 'categories': ('TextEditor','IDE'), 'names': ('code','visual studio code','antigravity','gedit','mousepad','kate','notepad','text editor','sublime','cursor')},
 'terminal': {'terms': ('terminal','console'), 'categories': ('TerminalEmulator',), 'names': ('terminal','konsole','kitty','alacritty','xterm')},
 'files': {'terms': ('file manager','files'), 'categories': ('FileManager',), 'names': ('files','nautilus','dolphin','thunar','nemo')},
}

def discover():
    found = {}
    for directory in SEARCH_DIRS:
        if not directory.is_dir():
            continue
        for path in directory.glob('*.desktop'):
            desktop_id = path.name
            if desktop_id in found:
                continue
            parser = configparser.ConfigParser(interpolation=None, strict=False)
            parser.optionxform = str
            try:
                parser.read(path, encoding='utf-8')
                entry = parser['Desktop Entry']
                if entry.get('Type','') != 'Application' or entry.get('Hidden','false').lower() == 'true' or entry.get('NoDisplay','false').lower() == 'true':
                    continue
                name = entry.get('Name','').strip()
                if not name or not entry.get('Exec'):
                    continue
                only = [x for x in entry.get('OnlyShowIn','').split(';') if x]
                excluded = [x for x in entry.get('NotShowIn','').split(';') if x]
                desktops = os.environ.get('XDG_CURRENT_DESKTOP','').split(':')
                if only and not any(x in desktops for x in only):
                    continue
                if any(x in desktops for x in excluded):
                    continue
                try_exec = entry.get('TryExec','').strip()
                if try_exec and not (Path(try_exec).is_file() if '/' in try_exec else shutil.which(try_exec)):
                    continue
                found[desktop_id] = {'id':desktop_id,'name':name,'categories':entry.get('Categories','').split(';')}
            except (OSError, configparser.Error, KeyError):
                continue
    return sorted(found.values(), key=lambda a: a['name'].casefold())

def category_for(text):
    text = text.casefold().strip()
    for group, spec in GROUPS.items():
        if text in spec['terms']:
            return group
    return None

def matches(app, category):
    spec = GROUPS[category]
    name = app['name'].casefold()
    cats = set(app['categories'])
    return bool(cats.intersection(spec['categories'])) or any(n in name for n in spec['names'])

def choose_and_launch(query):
    apps = discover()
    category = category_for(query)
    if category:
        candidates = [a for a in apps if matches(a,category)]
    else:
        q = query.casefold()
        candidates = [a for a in apps if q == a['name'].casefold() or q in a['name'].casefold()]
    if not candidates:
        print('Agent > No matching installed application found.')
        return
    if len(candidates) == 1:
        chosen = candidates[0]
    else:
        print('Agent > Available applications:')
        for i, app in enumerate(candidates,1):
            print(f'  {i}. {app["name"]}')
        answer = input('Choose number (or cancel): ').strip()
        if not answer.isdigit() or not 1 <= int(answer) <= len(candidates):
            print('Agent > Cancelled.')
            return
        chosen = candidates[int(answer)-1]
    if input(f'Launch {chosen["name"]}? [y/N] ').strip().lower() != 'y':
        print('Agent > Cancelled.')
        return
    if not shutil.which('gtk-launch'):
        print('Agent > gtk-launch is unavailable. Install libgtk-3-bin.')
        return
    try:
        subprocess.Popen(['gtk-launch',chosen['id']], stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL, start_new_session=True)
        print(f'Agent > Launch requested: {chosen["name"]}')
    except OSError as exc:
        print(f'Agent > Launch failed: {exc}')

def handle_app_request(user):
    match = re.fullmatch(r'\s*(?:open|launch|start)(?:\s+(?:the|my|a))?\s+(.+?)\s*[.!?]?\s*',user,re.I)
    if not match:
        return False
    target = match.group(1).strip()
    if target.casefold() in ('browser','web browser','internet browser','text editor','code editor','editor','ide','terminal','console','file manager','files'):
        choose_and_launch(target)
        return True
    apps = discover()
    if any(target.casefold() in app['name'].casefold() for app in apps):
        choose_and_launch(target)
        return True
    return False
