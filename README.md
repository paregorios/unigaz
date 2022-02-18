next:

- merge local places
- fetch and merge from externals (unless created from one of them)
- mine more externals out of pleiades references ctype=related
- add support for more external gazetteers
- save local gazetteer (to pickle? jsonpickle?)
- local local gazetteer (from pickle? jsonpickle?)
- export place, name, or entire local gazetteer to json, teixml, geojson, linked place format json, csv, markdown, html
- on place accession, grok names
- on place accession, grok locations
- when we have locations: map them
- map whole local gazetteer
- map search result set
- cli: edit individual bits of data with commands like: "set local 1 externals 1 lang=en"
- modify error handling so it doesn't swallow real development errors and their associated tracebacks
