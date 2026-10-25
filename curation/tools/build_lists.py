#!/usr/bin/env python3
"""Build the curated Sanskrit and Kannada composition lists from the repo data plus the curation overlay.

Inputs (nothing upstream is modified):
  Carnatic/song/*.json                    — the generated song records (title, info, lyrics, videos)
  curation/rules.json                     — classification rules (which forms are stotras, free-form, …)
  curation/carnatic/song_review.csv       — per-song language verdict and corrected IAST / ISO 15919 title
  curation/carnatic/dikshitar_samaharam.csv — Dīkṣitar works matched to P. P. Narayanaswami's 484-kṛti Samāhāram
  curation/carnatic/stotra_seed.csv       — a few well-known stotras the repo has no recording of

Outputs: curation/carnatic/lists/{sanskrit_composed,sanskrit_stotras,kannada_composed,kannada_freeform}.csv

Usage:  python3 curation/tools/build_lists.py            (from the repo root)
Optional: `pip install indic_transliteration` adds Devanagari / Kannada-script columns.
"""
import csv, json, os, re, sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CUR = os.path.join(ROOT, 'curation')
SONGS = os.path.join(ROOT, 'Carnatic', 'song')
OUT = os.path.join(CUR, 'carnatic', 'lists')

try:
    from indic_transliteration import sanscript
except ImportError:                      # script columns are optional
    sanscript = None


def to_devanagari(iast):
    return sanscript.transliterate(iast, sanscript.IAST, sanscript.DEVANAGARI) if (sanscript and iast) else ''


def to_kannada(iso):
    """House style: anusvāra (ಂ) for a nasal before a stop, ISO r̥ for vocalic r."""
    if not (sanscript and iso):
        return ''
    s = iso.replace('ṃ', 'ṁ').replace('ṝ', 'r̥̄').replace('ṛ', 'r̥')
    s = re.sub(r'[ṅñṇnm](?=[kgcjṭḍtdpb])', 'ṁ', s)
    return sanscript.transliterate(s, sanscript.ISO, sanscript.KANNADA)


def load_songs():
    songs = {}
    for fn in os.listdir(SONGS):
        if not fn.endswith('.json'):
            continue
        with open(os.path.join(SONGS, fn), encoding='utf-8') as f:
            d = json.load(f)
        info = {i.get('H'): i.get('V') for i in d.get('info', [])}
        stats = {s.get('H'): s.get('C') for s in d.get('stats', [])}
        refs = [l.get('L') for b in d.get('lyricsref') or [] for l in b.get('links', [])]
        songs[fn] = dict(file=fn, id=d['title'].get('T'), title=d['title'].get('H'), type=info.get('Type'), composer=info.get('Composer'),
                         raga=info.get('Raga'), tala=info.get('Tala'), language=info.get('Language'), deity=info.get('God'), kshetra=info.get('Kshetra'),
                         videos=int((stats.get('Videos') or '0').replace(',', '')), ref=refs[0] if refs else '')
    return songs


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, cols):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


RESOLUTION_LABELS = {'duplicate': 'Duplicate entry', 'attribution': 'Attribution doubtful', 'lyric_mismatch': 'Repo lyric is another song',
                     'language_unverified': 'Language unverified'}


def clean_raga(r):
    return '' if r in (None, 'Unknownraga') else ('Rāgamālikā' if r == 'Ragamalika' else r)


def composer(c):
    return 'Unattributed in source' if c in (None, 'UnknownComposer') else c


def main():
    rules = json.load(open(os.path.join(CUR, 'rules.json'), encoding='utf-8'))
    songs = load_songs()
    review = {r['song_file']: r for r in read_csv(os.path.join(CUR, 'carnatic', 'song_review.csv'))}
    samaharam = read_csv(os.path.join(CUR, 'carnatic', 'dikshitar_samaharam.csv'))
    res_path = os.path.join(CUR, 'carnatic', 'flag_resolutions.csv')
    resolutions = {r['song_file']: r for r in read_csv(res_path)} if os.path.exists(res_path) else {}
    SAN = set(rules['sanskrit_language_tags'])
    FORM, SERIES = rules['form_names'], rules['series_names']
    excl = re.compile(rules['exclude_note_pattern'], re.I)
    rs, rk = rules['sanskrit'], rules['kannada']
    stotra_note = re.compile(rs['stotra_note_pattern'], re.I)
    free_note = re.compile(rk['free_form_note_pattern'], re.I)

    composed, stotras, done = [], [], set()
    # 1. Dīkṣitar: title spelling from the Samāhāram
    for s in samaharam:
        files = [f for f in s['repo_song_files'].split(';') if f]
        if not files:
            if s['language'].lower().startswith('sanskrit') or not s['language']:
                composed.append(dict(title_iast=s['kriti_iast'], composer='Muthuswami Dikshitar', form='Kṛti', raga=s['raga'], tala=s['tala'],
                                     recordings=0, basis=f"Samāhāram #{s['samaharam_no']} (no recording in repo)", confidence=s['confidence'],
                                     check='' if s['confidence'] in ('high', 'med') else 'Rāga/tāla weakly sourced', note=s['note'], source=s['raga_tala_source']))
            continue
        for fn in files:
            g = songs.get(fn)
            if not g or (g['language'] and g['language'] not in SAN):
                continue
            done.add(fn)
            composed.append(dict(song_file=fn, song_id=g['id'], source_title=g['title'], title_iast=s['kriti_iast'], composer=g['composer'],
                                 form=FORM.get(g['type'], 'Kṛti'), series=SERIES.get(g['type'], ''), raga=clean_raga(g['raga']), tala=g['tala'] or '',
                                 deity=g['deity'] or '', kshetra=g['kshetra'] or '', recordings=g['videos'], source_language=g['language'] or '',
                                 basis=f"Samāhāram #{s['samaharam_no']}", source=g['ref']))
    # 2. Everything else, from the per-song review
    kannada_comp, kannada_free = [], []
    for fn, v in review.items():
        g = songs.get(fn)
        if not g or fn in done or excl.search(v['note'] or ''):
            continue
        lang, note = v['language'], v['note'] or ''
        if g['composer'] == 'Muthuswami Dikshitar' and not v['title_iast']:
            continue
        base = dict(song_file=fn, song_id=g['id'], source_title=g['title'], composer=composer(g['composer']), raga=clean_raga(g['raga']),
                    tala=g['tala'] or '', deity=g['deity'] or '', recordings=g['videos'], source_language=g['language'] or '',
                    confidence=v['confidence'], note=note, source=g['ref'])
        flags = []
        if v['confidence'] == 'low':
            flags.append('Low confidence (title only)')
        if lang == 'Sanskrit' or (lang == 'Unsure' and rs['include_unsure_if_source_tag_is_sanskrit'] and g['language'] in SAN):
            if not v['title_iast']:
                continue
            if g['language'] not in SAN:
                flags.append(f"Newly identified as Sanskrit (source: {g['language'] or 'untagged'})")
            is_stotra = (g['type'] in rs['stotra_types'] or g['composer'] in rs['stotra_authors'] or bool(stotra_note.search(note))
                         or (g['composer'] == 'Appayya Dikshitar' and g['type'] != 'Geetham'))
            form = FORM.get(g['type'], g['type'] or 'Kṛti')
            if g['composer'] in rs['taranga_composers'] and g['type'] == 'Krithi':
                form = 'Taraṅga'
            if is_stotra and g['type'] == 'Krithi':
                form = 'Stotra (set as kṛti)'
            row = dict(base, title_iast=v['title_iast'], form=form, series=SERIES.get(g['type'], ''), kshetra=g['kshetra'] or '',
                       basis='Reviewed', check='; '.join(flags))
            (stotras if is_stotra else composed).append(row)
        elif lang == 'Kannada':
            if g['language'] != 'Kannada':
                flags.append(f"Newly identified as Kannada (source: {g['language'] or 'untagged'})")
            free = g['type'] in rk['free_form_types'] or bool(free_note.search(note))
            c = g['composer'] or ''
            trad = 'Haridāsa' if c in rk['haridasa_composers'] or c.endswith('Dasa') else ''
            row = dict(base, title_iso=v['title_iso'], tradition=trad, form=FORM.get(g['type'], g['type'] or 'Kṛti / Dēvaranāma'), check='; '.join(flags))
            (kannada_free if free else kannada_comp).append(row)
    # 3. Well-known concert stotras the repo has no recording of
    seed_path = os.path.join(CUR, 'carnatic', 'stotra_seed.csv')
    for s in (read_csv(seed_path) if os.path.exists(seed_path) else []):
        stotras.append(dict(title_iast=s['title_iast'], source_title=s['title'], composer=s['author'], form=s['form'], recordings=0,
                            basis='Curated seed (no recording in repo)', note=s['note'], source=s['text_url']))
    # 4. Resolved flags: retitles, duplicates, doubtful attributions, mismatched lyrics
    for r in composed + stotras + kannada_comp + kannada_free:
        res = resolutions.get(r.get('song_file'))
        if not res:
            continue
        if res['set_title_iso']:
            r['title_iso'] = res['set_title_iso']
        if res['duplicate_of']:
            r['duplicate_of'] = res['duplicate_of']
        label = RESOLUTION_LABELS.get(res['action'])
        if label:
            r['check'] = '; '.join(x for x in (r.get('check'), label) if x)
        r['note'] = ' · '.join(x for x in (r.get('note'), res['resolution']) if x)
    for r in composed + stotras:
        r['title_devanagari'] = to_devanagari(r.get('title_iast'))
    for r in kannada_comp + kannada_free:
        r['title_kannada'] = to_kannada(r.get('title_iso'))
    os.makedirs(OUT, exist_ok=True)
    sc = ['title_iast', 'title_devanagari', 'source_title', 'composer', 'form', 'series', 'raga', 'tala', 'deity', 'kshetra', 'recordings',
          'source_language', 'basis', 'confidence', 'check', 'note', 'source', 'song_file', 'song_id', 'duplicate_of']
    kc = ['title_kannada', 'title_iso', 'source_title', 'composer', 'tradition', 'form', 'raga', 'tala', 'deity', 'recordings', 'source_language',
          'confidence', 'check', 'note', 'source', 'song_file', 'song_id', 'duplicate_of']
    key = lambda r: ((r.get('composer') or '').lower(), r.get('title_iast') or r.get('title_iso') or '')
    write_csv(os.path.join(OUT, 'sanskrit_composed.csv'), sorted(composed, key=key), sc)
    write_csv(os.path.join(OUT, 'sanskrit_stotras.csv'), sorted(stotras, key=key), sc)
    write_csv(os.path.join(OUT, 'kannada_composed.csv'), sorted(kannada_comp, key=key), kc)
    write_csv(os.path.join(OUT, 'kannada_freeform.csv'), sorted(kannada_free, key=key), kc)
    print(f'sanskrit composed {len(composed)} · stotras {len(stotras)} · kannada composed {len(kannada_comp)} · free-form {len(kannada_free)}')
    print('top Sanskrit composers:', Counter(r['composer'] for r in composed).most_common(5))


if __name__ == '__main__':
    sys.exit(main())
