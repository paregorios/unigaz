# unigaz

Shake and bake gazetteers.

## Goals/Principles

- Mix, match, and merge from other gazetteers/datasets, both local and online
- Be polite to web services (crawl-delay, robots.txt disallow, user agent string)
- Save/load/import/export from the common/standard formats
- Keep track of provenance of data
- Don't duplicate effort with other tools
- Free and open-source (extensible, customizable)
- Platform-independent 
- Quickly list/map/query what you've got

## Install

Using a python (v. 3.10.2 or higher) virtual environment for this project is **highly** recommended. Once you've got that set up ...

Needs a little more maturity before distribution via pypi, so for now, 

```
$ curl -L -O https://github.com/paregorios/unigaz/archive/refs/heads/main.zip
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   131  100   131    0     0    553      0 --:--:-- --:--:-- --:--:--   572
100 33573    0 33573    0     0  66778      0 --:--:-- --:--:-- --:--:-- 66778
$ unzip main
Archive:  main.zip
bc27c3c921a6fb93a4362a84f5a97d54c98df9eb
   creating: unigaz-main/
  inflating: unigaz-main/.gitignore  
  inflating: unigaz-main/LICENSE.txt  
  inflating: unigaz-main/MANIFEST.in  
  inflating: unigaz-main/README.md   
  inflating: unigaz-main/requirements_dev.txt  
   creating: unigaz-main/scripts/
  inflating: unigaz-main/scripts/cli.py  
  inflating: unigaz-main/setup.cfg   
  inflating: unigaz-main/setup.py    
   creating: unigaz-main/tests/
  inflating: unigaz-main/tests/test_pleiades.py  
   creating: unigaz-main/unigaz/
  inflating: unigaz-main/unigaz/edh.py  
  inflating: unigaz-main/unigaz/gazetteer.py  
  inflating: unigaz-main/unigaz/interpreter.py  
  inflating: unigaz-main/unigaz/local.py  
  inflating: unigaz-main/unigaz/manager.py  
  inflating: unigaz-main/unigaz/pleiades.py  
  inflating: unigaz-main/unigaz/web.py  
$ cd unigaz-main/
$ pip install -U -r requirements_dev.txt 
```

## Getting Started

In the package home directory, fire up the command-line interface:

```
$ python scripts/cli.py
WARNING:webiquette.robots_txt:No robots.txt found for edh.ub.uni-heidelberg.de.
UniGaz: Tools for working with digital gazetteers
type 'help' for a list of commands
> help

┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ command     ┃ documentation                                    ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ accession   │ Accession an item from search results into local │
│             │                                                  │
│ create      │ Create a local gazetteer.                        │
│             │                                                  │
│ gazetteer   │ Check for gazetteer support.                     │
│             │                                                  │
│ gazetteers  │ List supported gazetteers.                       │
│             │                                                  │
│ help        │ Get help with available commands.                │
│             │                                                  │
│ list        │ List contents of collections                     │
│             │                                                  │
│ log_debug   │ Change logging level to DEBUG                    │
│             │                                                  │
│ log_error   │ Change logging level to ERROR                    │
│             │                                                  │
│ log_info    │ Change logging level to INFO                     │
│             │                                                  │
│ log_level   │ Get the current logging level.                   │
│             │                                                  │
│ log_warning │ Change logging level to WARNING                  │
│             │                                                  │
│ map         │ Display a map of the indicated Place             │
│             │                                                  │
│ merge       │ Merge one local item into another                │
│             │                                                  │
│ quit        │ Quit interactive interface.                      │
│             │                                                  │
│ raw         │ Show raw data view of an item in a context list  │
│             │                                                  │
│ search      │ Conduct search in supported gazetteer(s).        │
│             │                                                  │
│ usage       │ Get usage for indicated command.                 │
└─────────────┴──────────────────────────────────────────────────┘
> 
```

### Create a new "local" (i.e., personal) gazetteer

```
> create my sites
Created local gazetteer with title 'my sites'.
> list local
my sites: 0 items          
┏━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ local context ┃ summary ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━┩
└───────────────┴─────────┘
> 
```

### Search an external gazetteer

Find places of interest and accession them to the local gazetteer.

```
> gazetteers
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ short name ┃ netloc                   ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ pleiades   │ pleiades.stoa.org        │
│            │                          │
│ edh        │ edh.ub.uni-heidelberg.de │
└────────────┴──────────────────────────┘
> search pleiades zucchabar
https://pleiades.stoa.org/search_rss?SearchableText=zucchabar&review_state=published&porta
l_type=Place
Search hits: 1                                                                            
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ context ┃ summary                                                                      ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1       │ Place: Zucchabar                                                             │
│         │ https://pleiades.stoa.org/places/295374                                      │
│         │ Zucchabar was an ancient city of Mauretania Caesariensis with Punic origins. │
│         │ The modern Algerian community of Miliana lies atop and around the largely    │
│         │ unexcavated ancient site. Epigraphic evidence indicates that the Roman       │
│         │ emperor Augustus established a veteran colony there.                         │
└─────────┴──────────────────────────────────────────────────────────────────────────────┘
> accession search 1
Created Place 'Zucchabar' from external source.'
> list local
my sites: 1 items                                                                         
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ local context ┃ summary                                                                ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1             │ Place: Zucchabar                                                       │
│               │ Zucchabar was an ancient city of Mauretania Caesariensis with Punic    │
│               │ origins. The modern Algerian community of Miliana lies atop and around │
│               │ the largely unexcavated ancient site. Epigraphic evidence indicates    │
│               │ that the Roman emperor Augustus established a veteran colony there.    │
└───────────────┴────────────────────────────────────────────────────────────────────────┘
> search edh zucchabar
https://edh.ub.uni-heidelberg.de/data/api/geographie/suche?limit=100&fo_modern=zucchabar; 
https://edh.ub.uni-heidelberg.de/data/api/geographie/suche?limit=100&fo_antik=zucchabar
Search hits: 1                                                       
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ context ┃ summary                                                 ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1       │ Place: Zucchabar - Miliana                              │
│         │ https://edh.ub.uni-heidelberg.de/edh/geographie/G013662 │
│         │ Ech Cheliff, Algeria                                    │
└─────────┴─────────────────────────────────────────────────────────┘
> accession search 1
Created Place 'Zucchabar - Miliana' from external source.'
> list local
my sites: 2 items                                                                         
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ local context ┃ summary                                                                ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1             │ Place: Zucchabar                                                       │
│               │ Zucchabar was an ancient city of Mauretania Caesariensis with Punic    │
│               │ origins. The modern Algerian community of Miliana lies atop and around │
│               │ the largely unexcavated ancient site. Epigraphic evidence indicates    │
│               │ that the Roman emperor Augustus established a veteran colony there.    │
│               │                                                                        │
│ 2             │ Place: Zucchabar - Miliana                                             │
│               │ Ech Cheliff, Algeria                                                   │
└───────────────┴────────────────────────────────────────────────────────────────────────┘
> 
```

### Map places in the local gazetteer

```
> list local
my sites: 2 items                                                                         
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ local context ┃ summary                                                                ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1             │ Place: Zucchabar                                                       │
│               │ Zucchabar was an ancient city of Mauretania Caesariensis with Punic    │
│               │ origins. The modern Algerian community of Miliana lies atop and around │
│               │ the largely unexcavated ancient site. Epigraphic evidence indicates    │
│               │ that the Roman emperor Augustus established a veteran colony there.    │
│               │                                                                        │
│ 2             │ Place: Zucchabar - Miliana                                             │
│               │ Ech Cheliff, Algeria                                                   │
└───────────────┴────────────────────────────────────────────────────────────────────────┘
> map local 1
Opening map in default browser: /temp/directory/somewhere/on/your/machine/xyzpdg42.html
```

You should see a map:

<img alt="Example map of possible locations of Zucchabar from Pleiades on OpenStreetMap base map" src="https://raw.githubusercontent.com/paregorios/unigaz/main/data/images/map_eg.png" style="max-width: 90%; max-height: 90%">

### Merge two places in your local gazeteer

```
> list local
my sites: 2 items                                                                         
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ local context ┃ summary                                                                ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1             │ Place: Zucchabar                                                       │
│               │ Zucchabar was an ancient city of Mauretania Caesariensis with Punic    │
│               │ origins. The modern Algerian community of Miliana lies atop and around │
│               │ the largely unexcavated ancient site. Epigraphic evidence indicates    │
│               │ that the Roman emperor Augustus established a veteran colony there.    │
│               │                                                                        │
│ 2             │ Place: Zucchabar - Miliana                                             │
│               │ Ech Cheliff, Algeria                                                   │
└───────────────┴────────────────────────────────────────────────────────────────────────┘
> merge 2 1
<unigaz.local.Place object at 0x11e146da0>
> list local
my sites: 2 items                                                                         
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ local context ┃ summary                                                                ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1             │ Place: Zucchabar                                                       │
│               │ Zucchabar was an ancient city of Mauretania Caesariensis with Punic    │
│               │ origins. The modern Algerian community of Miliana lies atop and around │
│               │ the largely unexcavated ancient site. Epigraphic evidence indicates    │
│               │ that the Roman emperor Augustus established a veteran colony there.    │
│               │ Zucchabar - Miliana                                                    │
│               │ Ech Cheliff, Algeria                                                   │
│               │                                                                        │
│ 2             │ Place: Zucchabar - Miliana                                             │
│               │ Ech Cheliff, Algeria                                                   │
└───────────────┴────────────────────────────────────────────────────────────────────────┘
> 
```

### Export the local gazetteer to JSON

```
> export json
Wrote 2 entries in local gazetteer to JSON file 
/the/directory/where/you/installed/unigaz/data/exports/my_sites_202202221915.json.
```

### Get detailed (raw) view of a place in your local gazetteer

The "raw" command lets you read on the command line the same JSON serialization used for the "export json" command:

```
> raw local 1
{
    'id': '9225f7b999ff423187ef5c4bc5862bb0',
    'title': 'Zucchabar',
    'descriptions': [
        {
            'text': 'Zucchabar was an ancient city of Mauretania Caesariensis with Punic 
origins. The modern Algerian community of Miliana lies atop and around the largely 
unexcavated ancient site. Epigraphic evidence indicates that the Roman emperor Augustus 
established a veteran colony there.',
            'lang': 'und',
            'preferred': False,
            'source': 'https://pleiades.stoa.org/places/295374/json'
        },
        {
            'text': 'Zucchabar - Miliana',
            'lang': 'und',
            'preferred': False,
            'source': None
        },
        {
            'text': 'Ech Cheliff, Algeria',
            'lang': 'und',
            'preferred': False,
            'source': 'https://edh.ub.uni-heidelberg.de/edh/geographie/G013662/json'
        }
    ],
    'externals': {
        'https://pleiades.stoa.org/places/295374': [
            'https://pleiades.stoa.org/places/295374/json',
            'https://edh.ub.uni-heidelberg.de/edh/geographie/G013662/json'
        ],
        'https://pleiades.stoa.org/places/295374/json': [
            'https://pleiades.stoa.org/places/295374/json'
        ],
        'https://edh.ub.uni-heidelberg.de/edh/geographie/G013662': [
            'https://edh.ub.uni-heidelberg.de/edh/geographie/G013662/json'
        ],
        'https://geonames.org/2487444': [
            'https://edh.ub.uni-heidelberg.de/edh/geographie/G013662/json'
        ],
        'https://trismegistos.org/place/20498': [
            'https://edh.ub.uni-heidelberg.de/edh/geographie/G013662/json'
        ],
        'https://edh.ub.uni-heidelberg.de/edh/geographie/G013662/json': [
            'https://edh.ub.uni-heidelberg.de/edh/geographie/G013662/json'
        ]
    },
    'journal': {
        '2022-02-22T15:33:00.815291+00:00': {'created': None},
        '2022-02-22T15:33:00.815335+00:00': {
            'created from': 'https://pleiades.stoa.org/places/295374/json'
        },
        '2022-02-22T15:34:23.012554+00:00': {
            'created from': 'https://edh.ub.uni-heidelberg.de/edh/geographie/G013662/json'
        },
        '2022-02-22T15:42:47.338109+00:00': {'merged_from': 'Zucchabar - Miliana'}
    },
    'locations': [
        {
            'id': '58391b0cd8fc4378840e48bea4eb2ee5',
            'title': 'DARMC location 15549',
            'descriptions': [
                {
                    'text': '500K scale point location',
                    'lang': 'und',
                    'preferred': False,
                    'source': 'https://pleiades.stoa.org/places/295374/json'
                }
            ],
            'externals': {
                'https://pleiades.stoa.org/places/295374/darmc-location-15549': [
                    'https://pleiades.stoa.org/places/295374/json'
                ],
                'https://pleiades.stoa.org/places/295374/json': [
                    'https://pleiades.stoa.org/places/295374/json'
                ],
                'https://pleiades.stoa.org/vocabularies/association-certainty/certain': [
                    'https://pleiades.stoa.org/places/295374/json'
                ],
                'https://pleiades.stoa.org/features/metadata/darmc-a': [
                    'https://pleiades.stoa.org/places/295374/json'
                ]
            },
            'journal': {
                '2022-02-22T15:33:00.816663+00:00': {'created': None},
                '2022-02-22T15:33:00.816989+00:00': {
                    'created from': 'https://pleiades.stoa.org/places/295374/json'
                }
            },
            'geometry': {'type': 'Point', 'coordinates': (2.223758, 36.304939)},
            'accuracy_radius': None,
            'source': 'https://pleiades.stoa.org/places/295374/json'
        },
        {
            'id': 'c5a62d413cc545cf8b392bc286b32727',
            'title': 'DARE Location',
            'descriptions': [
                {
                    'text': 'Representative point location, village precision',
                    'lang': 'und',
                    'preferred': False,
                    'source': 'https://pleiades.stoa.org/places/295374/json'
                }
            ],
            'externals': {
                'https://pleiades.stoa.org/places/295374/dare-location': [
                    'https://pleiades.stoa.org/places/295374/json'
                ],
                'https://pleiades.stoa.org/places/295374/json': [
                    'https://pleiades.stoa.org/places/295374/json'
                ],
                'https://pleiades.stoa.org/vocabularies/association-certainty/certain': [
                    'https://pleiades.stoa.org/places/295374/json'
                ],
                'https://pleiades.stoa.org/features/metadata/dare-2': [
                    'https://pleiades.stoa.org/places/295374/json'
                ]
            },
            'journal': {
                '2022-02-22T15:33:00.818548+00:00': {'created': None},
                '2022-02-22T15:33:00.818599+00:00': {
                    'created from': 'https://pleiades.stoa.org/places/295374/json'
                }
            },
            'geometry': {'type': 'Point', 'coordinates': (2.22619, 36.304782)},
            'accuracy_radius': 100.0,
            'source': 'https://pleiades.stoa.org/places/295374/json'
        },
        {
            'id': 'a0099338669e430c9b2b99fe1597cb0b',
            'title': 'EDH Coordinates',
            'descriptions': [],
            'externals': {},
            'journal': {
                '2022-02-22T15:34:23.012855+00:00': {'created': None},
                '2022-02-22T15:34:23.013239+00:00': {
                    'created from': 
'https://edh.ub.uni-heidelberg.de/edh/geographie/G013662/json'
                }
            },
            'geometry': {'type': 'Point', 'coordinates': (2.2248, 36.30554)},
            'accuracy_radius': None,
            'source': 'https://edh.ub.uni-heidelberg.de/edh/geographie/G013662/json'
        }
    ],
    'names': [
        {
            'id': '0029572bcd8c409b8b6aa119b7e8d214',
            'externals': {
                'https://pleiades.stoa.org/places/295374/zucchabar': [
                    'https://pleiades.stoa.org/places/295374/json'
                ],
                'https://pleiades.stoa.org/places/295374/json': [
                    'https://pleiades.stoa.org/places/295374/json'
                ],
                'https://pleiades.stoa.org/vocabularies/association-certainty/certain': [
                    'https://pleiades.stoa.org/places/295374/json'
                ]
            },
            'journal': {
                '2022-02-22T15:33:00.820112+00:00': {'created': None},
                '2022-02-22T15:33:00.820288+00:00': {
                    'created from': 'https://pleiades.stoa.org/places/295374/json'
                }
            },
            'attested_form': '',
            'romanized_forms': ['Zucchabar'],
            'language': 'und',
            'source': 'https://pleiades.stoa.org/places/295374/json',
            'name_type': 'geographic',
            'transcription_accuracy': 'accurate',
            'association_certainty': 'certain',
            'transcription_completeness': 'complete'
        },
        {
            'id': '263d554b1d4644ab80e8a89cf91a1918',
            'externals': {
                'https://pleiades.stoa.org/places/295374/zouchabbari': [
                    'https://pleiades.stoa.org/places/295374/json'
                ],
                'https://pleiades.stoa.org/places/295374/json': [
                    'https://pleiades.stoa.org/places/295374/json'
                ],
                'https://pleiades.stoa.org/vocabularies/association-certainty/certain': [
                    'https://pleiades.stoa.org/places/295374/json'
                ]
            },
            'journal': {
                '2022-02-22T15:33:00.821636+00:00': {'created': None},
                '2022-02-22T15:33:00.821787+00:00': {
                    'created from': 'https://pleiades.stoa.org/places/295374/json'
                }
            },
            'attested_form': 'Ζουχάββαρι',
            'romanized_forms': ['Zouchábbari, Zouchabbari'],
            'language': 'grc',
            'source': 'https://pleiades.stoa.org/places/295374/json',
            'name_type': 'geographic',
            'transcription_accuracy': 'accurate',
            'association_certainty': 'certain',
            'transcription_completeness': 'complete'
        },
        {
            'id': 'c36bd94e608349308c1899a871e5c272',
            'externals': {},
            'journal': {
                '2022-02-22T15:34:23.013324+00:00': {'created': None},
                '2022-02-22T15:34:23.013391+00:00': {
                    'created_from': 
'https://edh.ub.uni-heidelberg.de/edh/geographie/G013662/json'
                }
            },
            'attested_form': 'Miliana',
            'romanized_forms': ['Miliana'],
            'language': 'de',
            'source': 'https://edh.ub.uni-heidelberg.de/edh/geographie/G013662/json',
            'name_type': None,
            'transcription_accuracy': None,
            'association_certainty': None,
            'transcription_completeness': None
        },
        {
            'id': '09649c6e2f7e41088cbd19c04f5c0591',
            'externals': {},
            'journal': {
                '2022-02-22T15:34:23.013421+00:00': {'created': None},
                '2022-02-22T15:34:23.013444+00:00': {
                    'created from': 
'https://edh.ub.uni-heidelberg.de/edh/geographie/G013662/json'
                }
            },
            'attested_form': None,
            'romanized_forms': ['Zucchabar'],
            'language': 'und',
            'source': 'https://edh.ub.uni-heidelberg.de/edh/geographie/G013662/json',
            'name_type': None,
            'transcription_accuracy': None,
            'association_certainty': None,
            'transcription_completeness': None
        }
    ]
}
> 
```

## Next/Later/Maybe

- [x] merge local places
- [x] on place accession, grok names
- [x] on place accession, grok locations
- [x] when we have locations for a place: map them (and the horizontal accuracy bubble if there is one)
- [ ] export place, name, or entire local gazetteer to json, teixml, geojson, linked place format json, csv, markdown, html
    - [x] export to JSON
        - [x] gazetteer
        - [ ] place
    - [ ] export to GeoJSON (verify can import to QGIS)
    - [ ] export to linked places format JSON
    - [ ] export to markdown
    - [ ] export to HTML
- [ ] tests!
- [ ] fetch and merge from externals (unless created from one of them)
- [ ] mine more externals out of pleiades references ctype=related
- [ ] refactor and centralize language code parsing, language guessing, and romanization so as to hide package dependencies from all the gazetteer modules and consolidate them in a single place
- [ ] add support for more external gazetteers
    - [x] pleiades
    - [x] EDH Geo
    - [x] nominatim
    - [x] GeoNames
    - [ ] TGAZ/China Historical GIS (REST/JSON API)
    - [ ] iDAI Gazetteer (API: https://gazetteer.dainst.org/app/#!/help)
    - [ ] geo-kima (REST/JSON API)
    - [ ] Wikidata (SPARQL query API)
    - [ ] ToposText (does not have API, but does have bulk dataset download)
    - [ ] Syriac Gazetteer
    - [ ] AdriAtlas
    - [ ] FastiOnline
    - [ ] Chronique (OAI API seems to be broken)
    - [ ]
- [ ] save local gazetteer (to pickle? jsonpickle?)
- [ ] load local gazetteer (from pickle? jsonpickle?)
- [ ] map whole local gazetteer
- [ ] map search result set
- [ ] cli: edit individual bits of data with commands like: "set local 1 externals 1 lang=en"
- [ ] modify error handling so it doesn't swallow real development errors and their associated tracebacks
