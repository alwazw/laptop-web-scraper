"""Simple agent action logger

Usage examples:
  python scripts/agent_log.py add --action "Ran live scrape (amazon)" --status ongoing --details "0 items returned" --errors "['No prices in product nodes']"
  python scripts/agent_log.py set-unresolved "Amazon prices missing from product nodes"
  python scripts/agent_log.py show
"""
import json
import argparse
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parents[0].parent / 'logs' / 'agent_log.json'


def _load():
    if not LOG_FILE.exists():
        return {"entries": [], "unresolved": []}
    return json.loads(LOG_FILE.read_text(encoding='utf-8'))


def _save(data):
    LOG_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')


def add_entry(action, status='ongoing', details=None, errors=None):
    data = _load()
    entry = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'action': action,
        'status': status,
        'details': details or '',
        'errors': errors or []
    }
    data['entries'].append(entry)
    _save(data)
    print('Logged entry')


def set_unresolved(text):
    data = _load()
    data['unresolved'] = [text]
    _save(data)
    print('Set unresolved:', text)


def append_unresolved(text):
    data = _load()
    lst = data.get('unresolved', [])
    if text not in lst:
        lst.append(text)
    data['unresolved'] = lst
    _save(data)
    print('Appended unresolved:', text)


def show():
    data = _load()
    print(json.dumps(data, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')

    p_add = sub.add_parser('add')
    p_add.add_argument('--action', required=True)
    p_add.add_argument('--status', default='ongoing')
    p_add.add_argument('--details')
    p_add.add_argument('--errors', nargs='*')

    p_set = sub.add_parser('set-unresolved')
    p_set.add_argument('text')

    p_app = sub.add_parser('append-unresolved')
    p_app.add_argument('text')

    p_res = sub.add_parser('resolve')
    p_res.add_argument('text')
    p_res.add_argument('--notes', default='')

    p_clear = sub.add_parser('clear-unresolved')

    p_feat = sub.add_parser('feature-done')
    p_feat.add_argument('text')
    p_feat.add_argument('--notes', default='')

    p_show = sub.add_parser('show')

    args = parser.parse_args()
    if args.cmd == 'add':
        add_entry(args.action, args.status, args.details, args.errors)
    elif args.cmd == 'set-unresolved':
        set_unresolved(args.text)
    elif args.cmd == 'append-unresolved':
        append_unresolved(args.text)
    elif args.cmd == 'resolve':
        # Remove from unresolved list and add a done entry
        data = _load()
        unresolved = data.get('unresolved', [])
        if args.text in unresolved:
            unresolved.remove(args.text)
            data['unresolved'] = unresolved
            _save(data)
            add_entry(f'Resolved: {args.text}', status='done', details=args.notes)
            print('Resolved and logged:', args.text)
        else:
            print('Text not found in unresolved list')
    elif args.cmd == 'clear-unresolved':
        data = _load()
        data['unresolved'] = []
        _save(data)
        print('Cleared unresolved list')
    elif args.cmd == 'feature-done':
        add_entry(f'Feature Done: {args.text}', status='done', details=args.notes)
        print('Feature marked done and logged')
    else:
        show()