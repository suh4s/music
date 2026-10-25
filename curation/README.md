# curation/ — curated lists layered on the generated data

The `Carnatic/` and `Hindustani/` folders are generated upstream (Raman Arunachalam's pipeline) and re-synced
regularly. Everything in `curation/` sits **beside** that data and never edits it, so upstream syncs merge cleanly.
Each curated judgement is keyed to a song file (`Carnatic/song/<name>.json`) and its id (`title.T`).

## Layout

| Path | What it is |
|---|---|
| `rules.json` | Classification rules: which forms count as stotras or free-form, composer sets, display names for forms and series |
| `carnatic/song_review.csv` | One row per reviewed song: language verdict, confidence, corrected IAST (Sanskrit) or ISO 15919 (Kannada) title, note |
| `carnatic/dikshitar_samaharam.csv` | Muttusvāmi Dīkṣitar's 484 kṛtis from P. P. Narayanaswami's *Kīrtana Samāhāram* (guruguha.org, 2007), with the repo song files matched to each and rāga/tāla sources for the 34 with no recording |
| `carnatic/flag_resolutions.csv` | How each flagged row was resolved: retitles, duplicate entries (`duplicate_of`), doubtful attributions, repo lyrics that belong to another song |
| `carnatic/attributions.csv` | Composers for works the repo leaves unattributed, from research (Oct 2026): name used, name as found, role (composer / words / text), dates, confidence, evidence and source URLs. Rows with `apply=yes` (high/med) fill the composer column of the lists and are flagged “Composer from research”; the rest are leads. `set_form` corrects the form (bhajan, bhāvagīte, lakṣaṇa gīta…) |
| `carnatic/lyric_links.csv` | Extra lyric links for works whose repo entry has none, matched offline (title + rāga + composer) against karnatik.com's and shivkumar.org's song indexes; used by the companion and practice notebook |
| `carnatic/stotra_seed.csv` | A few well-known concert stotras the repo has no recording of (e.g. Śyāmalā Daṇḍakam) |
| `carnatic/lists/*.csv` | **Generated** by `tools/build_lists.py`: Sanskrit composed works, Sanskrit stotras & ślokas, Kannada composed works, Kannada free-form (ugābhōga, vacana, padya) |
| `carnatic/bmk_compositions.csv` | M. Balamuralikrishna's compositions (repo + published sources), with mēḷa numbers for the Janaka Kṛti Mañjarī |
| `carnatic/bmk_recordings_index.csv` | Every item on *Music for Posterity : Sreenivasa Murthy* and *musiquebox* where BMK performs or the piece is his, with time-stamped links |
| `carnatic/aarati_{kannada,sanskrit}.csv` | Āratī, maṅgaḷa and śōbhāne songs for deities, people and occasions, with rāga and recordings; lyrics in Kannada script, Devanagari and IAST where the text may be republished (repo and Wikisource texts), a link otherwise |
| `tools/build_lists.py` | Rebuilds `carnatic/lists/` from the song files + overlay |
| `tools/apply_language_fixes.py` | **Opt-in**: writes reviewed languages back into the song files' `info` in upstream's own format (dry run by default) |

## How the lists are classified

- **Language** comes from `song_review.csv`, not the source tag. Every row was re-read from its title and, where the repo has
  them, its lyrics. The source tag is often wrong: e.g. Muthiah Bhāgavatar's pieces open with Sanskrit vocatives but
  continue in Kannada or Telugu, and many Sanskrit works are tagged Telugu or carry no tag at all.
  An independent re-check of random samples found ≈1.8% errors in Sanskrit titles and ≈12% (mostly minor) in Kannada titles;
  a second pass then re-checked every Kannada title against its first lyric line (103 corrected, 15 flagged in `note`).
- **Sanskrit composed vs stotras:** composed = song forms whose setting the composer or sampradāya fixed (kṛti, varṇa,
  aṣṭapadī, taraṅga, navāvaraṇa…); stotras & ślokas = recited literature performers set to rāgas of their choice.
- **Kannada composed vs free-form:** tāla-bound songs vs ugābhōga / vacana / padya.
- **Composers missing from the source:** 352 listed works had no composer. Two research passes (Oct 2026): web search
  and page fetches (rasikas.org, Wikipedia, shlokam.org, Haridāsa works lists, label track lists, the composer credits on
  each work's own YouTube recordings), plus an offline match against karnatik.com's full song index. 187 are now credited
  (50 high: a reference page or two independent sources name the work; 137 med: one weaker source such as a recording's
  composer credit). Independent re-checks: 21 of 30 and 10 of 12 sampled attributions confirmed, the rest partly supported
  (role or title wording), none contradicted. 51 weaker leads are kept with `apply=no`; 159 works stay "Unattributed in source".
- **Spelling house style (IAST):** ṃ before a consonant, m before a vowel and at the end; homorganic nasals inside words
  (nanda, śaṅkara); avagraha as `'`. Dīkṣitar titles follow the Samāhāram.

## Rebuild

```bash
pip install indic_transliteration      # optional: adds Devanagari / Kannada-script columns
python3 curation/tools/build_lists.py
```

## Pushing fixes into the site data (optional)

`python3 curation/tools/apply_language_fixes.py` reports how many song files a fix would touch (1,870 at
`high` confidence). `--write` applies it. Leave it unapplied to keep the fork identical to upstream; re-run after each sync if you apply it.
