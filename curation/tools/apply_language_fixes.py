#!/usr/bin/env python3
"""Optionally push reviewed language verdicts back into Carnatic/song/*.json, in the repo's own format.

This is OPT-IN. By default it only reports what it would change (dry run). The song files are generated
upstream, so edits made here are overwritten on the next upstream sync — keep curation/carnatic/song_review.csv
as the source of truth and re-run this script after syncing if you want the site to show the fixes.

It only touches the `Language` entry of `info`, written exactly as upstream writes it:
    {"H": "Language", "V": "<Language>", "P": "<Language>", "I": 0}
and only for verdicts with confidence "high" (change with --min-confidence).

Usage (from the repo root):
    python3 curation/tools/apply_language_fixes.py                 # dry run: counts + examples
    python3 curation/tools/apply_language_fixes.py --write         # rewrite the affected song files
"""
import argparse, csv, json, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SONGS = os.path.join(ROOT, 'Carnatic', 'song')
REVIEW = os.path.join(ROOT, 'curation', 'carnatic', 'song_review.csv')
LANGS = {'Sanskrit', 'Kannada', 'Telugu', 'Tamil', 'Malayalam', 'Hindi', 'Marathi', 'Manipravalam'}
RANK = {'low': 0, 'med': 1, 'high': 2}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true', help='actually rewrite the song files')
    ap.add_argument('--min-confidence', default='high', choices=list(RANK))
    a = ap.parse_args()
    changes = []
    with open(REVIEW, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['language'] not in LANGS or RANK.get(r['confidence'], 0) < RANK[a.min_confidence]:
                continue
            src = r['source_language'] or ''
            canon = 'Sanskrit' if src in ('Sanaskrit', 'Sanksrit') else src
            if canon == r['language']:
                continue
            changes.append((r['song_file'], src, r['language']))
    print(f'{len(changes)} song files would change (confidence ≥ {a.min_confidence}).')
    for fn, old, new in changes[:15]:
        print(f'  {fn}: {old or "(none)"} → {new}')
    if not a.write:
        print('Dry run — pass --write to apply.')
        return
    for fn, old, new in changes:
        path = os.path.join(SONGS, fn)
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        info = d.setdefault('info', [])
        entry = next((i for i in info if i.get('H') == 'Language'), None)
        if entry is None:
            info.append({'H': 'Language', 'V': new, 'P': new, 'I': 0})
        else:
            entry['V'] = entry['P'] = new
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(d, f)       # upstream style: one line, ASCII with \u escapes
    print(f'Wrote {len(changes)} files.')


if __name__ == '__main__':
    main()
