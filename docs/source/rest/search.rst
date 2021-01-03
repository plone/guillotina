Search Endpoint
===============

Aggregation endpoint
--------------------

Verb: GET
Description: Get aggregation for a search
Endpoint: @aggregation

Example::

	@aggregation?title__eq=my+title&metadata=title,creators
	{
		'title': {
			'items': {
				'Item2': 1
			},
			'total': 1
		},
		'creators': {
			'items': {
				'root': 1
			},
			'total': 1
		}
	}


Search endpoint
---------------

Verb: GET
Description: Search for resources.
Endpoint: @search

Use cases:
  - Search for specific sentence on text field
  - Search for words on text field
  - Search for not having a value on a field
  - Search for wildcard on text field
  - Search for keyword on filter
  - Search for number and comparisons on numeric field
  - Search for paths

  - Define from which element you want to search
  - Define the search size return
  - Define metadata included and excluded on the result
  - Return full objects

### Implementation details

A list::

	query : term=first+second+third
	result : term = first, second, third

Text field search specific text/sentence::

	query : title__eq=my+sentence

Text field search words text::

	query : title__in=my+sentence

Text field search not words text::

	query : title__not=not+willing+words

Text field search wildcard text::

	query : title__wildcard=will*

Keyword on filter::

	query : subject=guillotina

Number on field::

	query : age=39
	query : age__gte=39
	query : age__lte=39

Date on field::

	query : creation=10-09-2018
	query : creation__gte=10-09-2018
	query : creation__lte=10-09-2018

Which metadata to return::

	query : _metadata=title+description
	query : _metadata_not=language+description

Sort::

	query : _sort_asc=age

Search size::

	query : _size=30

From which element to return::

	query : _from=30

Search for paths::

	query : path__starts=plone+folder
	result : elements on /plone/folder

Escape +::

	query : term=hola++adeu
	result : term=hola+adeu

Return full object::

	query : _fullobject=true


### Examples:

Plone call::

	GET /plone/@search?path.query=%2Ffolder&path.depth=2

Guillotina call::
	GET @search?path_starts=folder&depth_gte=2

Plone call::

	GET /plone/@search?Title=lorem&portal_type=Document

Guillotina call::
	
	GET @search?title_in=lorem&portal_type=Document

Plone call::

	GET /plone/@search?Title=lorem&portal_type=Document&review_state=published&facet=true&facet_field:list=portal_type&facet_field:list=review_state

Guillotina call::

	GET @search?title_in=lorem&portal_type=Document&review_state=published&_aggregations=portal_type+review_state


## Get index and metadata endpoint

Verb: GET
Description: Get Indexes information
Endpoint: @metadata

Result::

	JSON Schema for each type

Example::

	{
		“Document”: {
			“type”: “object”
			“properties”: {
				“text”: “string”
			}
		},
		“guillotina.behaviors.dublincore.IDublinCore”: {
			“type”: “object”,
			“properties”: {
				“titol”: “string”,
				“creation_date”: “date”,
				…
			}
		}
	}
