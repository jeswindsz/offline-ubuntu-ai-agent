import json
import shutil
import subprocess
from pathlib import Path
from ollama import chat

ROOT = (Path.home() / 'AI-Agent-Workspace').resolve()
ROOT.mkdir(exist_ok=True)
MODEL = 'qwen3:1.7b'
APPS = {'firefox': ['firefox'], 'files': ['nautilus'], 'terminal': ['gnome-terminal'], 'code': ['code']}

def safe_path(value):
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('Path outside approved workspace')
    return path

def perform(name, args):
    path = safe_path(args.get('path', '.')) if name != 'open_app' else None
    if name == 'list_files':
        return '\n'.join(sorted(p.name + ('/' if p.is_dir() else '') for p in path.iterdir())) or '(empty)'
    if name == 'read_file':
        if path.stat().st_size > 100_000:
            raise ValueError('File too large to read')
        return path.read_text(encoding='utf-8')
    if name == 'create_folder':
        path.mkdir(parents=True, exist_ok=False)
        return f'Created {path}'
    if name == 'write_file':
        if path.exists():
            raise ValueError('File exists; overwriting is disabled')
        path.parent.mkdir(parents=True, exist_ok=True)
        content = str(args.get('content', ''))
        if len(content) > 100_000:
            raise ValueError('Content too long')
        path.write_text(content, encoding='utf-8')
        return f'Created {path}'
    if name == 'move_file':
        destination = safe_path(args['destination'])
        if destination.exists():
            raise ValueError('Destination already exists')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(destination))
        return f'Moved to {destination}'
    if name == 'copy_file':
        destination = safe_path(args['destination'])
        if destination.exists():
            raise ValueError('Destination already exists')
        if path.is_dir():
            shutil.copytree(path, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        return f'Copied to {destination}'
    if name == 'open_app':
        app = str(args.get('app', '')).lower()
        if app not in APPS:
            raise ValueError(f'Unsupported app. Choose: {", ".join(APPS)}')
        subprocess.Popen(APPS[app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f'Launched {app}'
    raise ValueError('Unknown tool')

TOOLS = [
    {'type':'function','function':{'name':'list_files','description':'List workspace folder contents','parameters':{'type':'object','properties':{'path':{'type':'string'}},'required':['path']}}},
    {'type':'function','function':{'name':'read_file','description':'Read a small UTF-8 text file','parameters':{'type':'object','properties':{'path':{'type':'string'}},'required':['path']}}},
    {'type':'function','function':{'name':'create_folder','description':'Create a new directory','parameters':{'type':'object','properties':{'path':{'type':'string'}},'required':['path']}}},
    {'type':'function','function':{'name':'write_file','description':'Create a new text file, never overwrite','parameters':{'type':'object','properties':{'path':{'type':'string'},'content':{'type':'string'}},'required':['path','content']}}},
    {'type':'function','function':{'name':'move_file','description':'Move or rename file or folder','parameters':{'type':'object','properties':{'path':{'type':'string'},'destination':{'type':'string'}},'required':['path','destination']}}},
    {'type':'function','function':{'name':'copy_file','description':'Copy file or folder','parameters':{'type':'object','properties':{'path':{'type':'string'},'destination':{'type':'string'}},'required':['path','destination']}}},
    {'type':'function','function':{'name':'open_app','description':'Launch approved desktop app','parameters':{'type':'object','properties':{'app':{'type':'string','enum':list(APPS)}},'required':['app']}}},
]

messages = [{'role':'system','content':f'You are a local Ubuntu assistant. File operations are restricted to {ROOT}. Use tools for real actions. Never claim an action succeeded unless a tool confirms it. Paths are relative to workspace. No arbitrary shell commands.'}]
print(f'Offline Ubuntu Agent ({MODEL}) | Workspace: {ROOT} | type exit to quit')
while True:
    try:
        user = input('\nYou > ').strip()
        if user.lower() in ('exit','quit'):
            break
        if not user:
            continue
        messages.append({'role':'user','content':user})
        for _ in range(6):
            response = chat(model=MODEL, messages=messages, tools=TOOLS, think=False, options={'temperature':0,"num_ctx": 2048,"num_predict": 128})
            message = response.message
            messages.append(message)
            if not message.tool_calls:
                print('Agent >', message.content or '(No response)')
                break
            for call in message.tool_calls:
                name, args = call.function.name, call.function.arguments
                print(f'\nProposed: {name}({json.dumps(args, ensure_ascii=False)})')
                approved = input('Allow? [y/N] ').strip().lower() == 'y'
                try:
                    result = perform(name, args) if approved else 'DENIED by user'
                except Exception as error:
                    result = f'ERROR: {error}'
                print('Result:', result)
                messages.append({'role':'tool','tool_name':name,'content':result})
        else:
            print('Agent > Stopped: too many tool steps')
    except (KeyboardInterrupt, EOFError):
        break
    except Exception as error:
        print('Error:', error)
