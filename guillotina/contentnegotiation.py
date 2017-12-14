from guillotina._settings import app_settings
from guillotina.component import get_utility
from guillotina.interfaces import IContentNegotiation
from guillotina.interfaces import IDownloadView
from guillotina.interfaces import IRendererFormatRaw
from zope.interface import implementer

import logging


log = logging.getLogger(__name__)
log.setLevel(40)


class AcceptParameters(object):
    """
    AcceptParameters represents all of the possible aspects of Content
    Negotiation as a single object.  It is used to represent a combination
    of content type, language, encoding and charset which is either
    explicitly supported by the server or requested by the client.

    To create an AcceptParameters object, initialise with any of the
    Conneg options:

    AcceptParameters(content_type, language, encoding, charset)

    (using unnamed parameters if using them in this order)

    AcceptParameters(language=language, charset=charset)

    (using named parameters if using partial and/or out of order parameters)

    The content_type argument must be a ContentType object,
    The language argument must be a Language object
    The encoding argument must be a string
    The charset argument must be a string

    For example:

    ap = AcceptParameters(ContentType("text/html"), Language("en"))
    """
    def __init__(
            self, content_type=None, language=None, encoding=None,
            charset=None, packaging=None):
        self.content_type = content_type
        self.language = language
        self.encoding = encoding
        self.charset = charset
        self.packaging = packaging

    def matches(
            self, other, ignore_language_variants=False, as_client=True,
            packaging_wildcard=False):
        """
        Do this set of AcceptParameters match the other set of AcceptParameters.
        This is not the same as equivalence, especially if the ignore_language_variants
        and as_client arguments are set.

        ignore_language_variants will ensure that en matches en-gb, and so on
        as_client will ensure that this object acts as a client parameter, and therefore
            will implicitly ignore language variants
        packaging_wildcard will allow the packaging parameter to be * in either or both
        cases and still match
        """
        if other is None:
            return False
        ct_match = self.content_type.matches(other.content_type) \
            if self.content_type is not None else True

        e_match = self.encoding == other.encoding
        c_match = self.charset == other.charset
        p_match = False
        if packaging_wildcard:
            p_match = (self.packaging is None or
                       other.packaging is None or
                       self.packaging == other.packaging)
        else:
            p_match = self.packaging == other.packaging
        l_match = self.language.matches(other.language, ignore_language_variants, as_client) \
            if self.language is not None else True

        return ct_match and l_match and e_match and c_match and p_match

    def media_format(self):
        """
        This provides a convenient method to canonically represent the accept
        parameters using the language of media formats.
        """
        params = ""
        if self.content_type is not None:
            params += "(type=\"" + str(self.content_type.mimetype()) + "\") "
        if self.language is not None:
            params += "(lang=\"" + str(self.language) + "\") "
        if self.encoding is not None:
            params += "(encoding=\"" + str(self.encoding) + "\") "
        if self.charset is not None:
            params += "(charset=\"" + str(self.charset) + "\") "
        if self.packaging is not None:
            params += "(packaging=\"" + str(self.packaging) + "\") "
        mf = "(& " + params + ")"
        return mf

    def __eq__(self, other):
        return self.media_format() == other.media_format()

    def __str__(self):
        s = "AcceptParameters:: "
        if self.content_type is not None:
            s += "Content Type: " + str(self.content_type) + ";"
        if self.language is not None:
            s += "Language: " + str(self.language) + ";"
        if self.encoding is not None:
            s += "Encoding: " + str(self.encoding) + ";"
        if self.charset is not None:
            s += "Charset: " + str(self.charset) + ";"
        if self.packaging is not None:
            s += "Packaging: " + str(self.packaging) + ";"
        return s

    def __repr__(self):
        return str(self)


class Language(object):
    """
    Class to represent a language code as per the conneg spec.

    Languages can have a main language term and a language variant.
    For example:
        en  - English
        en-gb   - British English
    """
    def __init__(self, range=None, language=None, variant=None):
        """
        This object can be initiased in 2 ways:
            1/ With a Language range, containing the language and optionally the variant parts:
                lang = Language("en-us")
                lang = Language("cz")
            2/ With one or both of the language and variants specified separately:
                lang = Language(language="en", variant="gb")
                lang = Language(language="de")
        """
        if range is not None:
            self.language, self.variant = self._from_range(range)
        else:
            self.language = language
            self.variant = variant

    def matches(self, other, ignore_language_variants=False, as_client=True):
        """
        Does this language match the other language.  This is not strictly
        equivalence, depending on the ignore_language_variants and as_client
        arguments

        ignore_language_variants will cause this operation to only look for
            matches on the main language part (e.g. en will match en-us and en-gb)

        as_client will cause this operation to ignore language variants from
            the client only
        """
        if other is None:
            return False

        if self.language == "*" or other.language == "*":
            return True

        l_match = self.language == other.language
        v_match = self.variant == other.variant

        if as_client and self.variant is None and other.variant is not None:
            v_match = True
        elif as_client and self.variant is not None and other.variant is None:
            if ignore_language_variants:
                v_match = True

        return l_match and v_match

    def _from_range(self, range):
        """
        parse the lang and variant from the supplied range
        """
        lang_parts = range.split("-")
        if len(lang_parts) == 1:
            return lang_parts[0], None
        elif len(lang_parts) == 2:
            lang = lang_parts[0]
            sublang = lang_parts[1]
            return lang, sublang

    def __eq__(self, other):
        return str(self) == str(other)

    def __str__(self):
        s = str(self.language)
        if self.variant is not None:
            s += "-" + str(self.variant)
        return s

    def __repr__(self):
        return str(self)


class ContentType(object):
    """
    Class to represent a content type (mimetype) requested through content negotiation
    """
    def __init__(self, mimetype=None, type=None, subtype=None, params=None):
        """
        There are 2 ways to instantiate this object.
            1/ With just the mimetype
                ct = ContentType("text/html")
                ct = ContentType("application/atom+xml;type=entry")
            2/ With the parts of the Content Type
                ct = ContentType(type="application", subtype="atom+xml", params="type=entry")

        Properties:
        mimetype - the standard mimetype
        type    - the main type of the content.  e.g. in text/html, the type is "text"
        subtype - the subtype of the content.  e.g. in text/html the subtype is "html"
        params  - as per the mime specification, his represents the parameter extension
                  to the type, e.g. with application/atom+xml;type=entry, the params
                  are "type=entry"

        So, for example:
        application/atom+xml;type=entry => type="application", subtype="atom+xml",
        params="type=entry"
        """
        self.type = None
        self.subtype = None
        self.params = None

        if mimetype is not None:
            self.from_mimetype(mimetype)
        else:
            self.type = type
            self.subtype = subtype
            self.params = params

    def from_mimetype(self, mimetype):
        """
        Construct this object from the mimetype
        """
        # mimetype is of the form <supertype>/<subtype>[;<params>]
        parts = mimetype.split(";")
        if len(parts) == 2:
            self.type, self.subtype = parts[0].split("/", 1)
            self.params = parts[1]
        elif len(parts) == 1:
            self.type, self.subtype = parts[0].split("/", 1)

    def mimetype(self):
        """
        Turn the content type into its mimetype representation
        """
        mt = self.type + "/" + self.subtype
        if self.params is not None:
            mt += ";" + self.params
        return mt

    def matches(self, other):
        """
        Determine whether this ContentType and the supplied other ContentType are matches.
        This includes full equality
        or whether the wildcards (*) which can be supplied for type or subtype properties
        are in place in either partner in the match.

        For example:
            text/html matches */*
            text/html matches text/*
            text/html does not match image/*
            and so on
        """
        # assume None to be a wildcard
        if other is None:
            return False

        tmatch = self.type == "*" or other.type == "*" or self.type == other.type
        smatch = self.subtype == "*" or other.subtype == "*" or self.subtype == other.subtype
        # FIXME: there is some ambiguity in mime as to whether the omission of the params part
        # is the same as a wildcard.  For the purposes of convenience we have assumed here
        # that it is, otherwise a request for */* will not match any content type which has
        # parameters
        pmatch = self.params is None or other.params is None or self.params == other.params

        return tmatch and smatch and pmatch

    def __eq__(self, other):
        return self.mimetype() == other.mimetype()

    def __str__(self):
        return self.mimetype()

    def __repr__(self):
        return str(self)


# Main Content Negotiation Objects
##################################

class ContentNegotiator(object):
    """
    Class to manage content negotiation.

    Basic Usage
    -----------

    # Import all the objects from the negotiator module
    >>> from negotiator import ContentNegotiator, AcceptParameters, ContentType, Language

    # Specify the default parameters.  These are the parameters which will be used in
    # place of any HTTP Accept headers which are not present in the negotiation request
    # For example, if the Accept-Language header is not passed to the negotiator
    # it will assume that the client request is for "en"
    >>> default_params = AcceptParameters(ContentType("text/html"), Language("en"))

    # Specify the list of acceptable formats that the server supports
    >>> acceptable = [AcceptParameters(ContentType("text/html"), Language("en"))]
    >>> acceptable.append(AcceptParameters(ContentType("text/json"), Language("en")))

    # Create an instance of the negotiator, ready to accept negotiation requests
    >>> cn = ContentNegotiator(default_params, acceptable)

    # A simple negotiate on the HTTP Accept header "text/json;q=1.0, text/html;q=0.9",
    # asking for json, and if not json then html
    >>> acceptable = cn.negotiate(accept="text/json;q=1.0, text/html;q=0.9")

    # The negotiator indicates that the best match the server can give to the
    # client's request is text/json in english
    >>> acceptable
    AcceptParameters:: Content Type: text/json;Language: en;

    Advanced Usage
    --------------

    # Import all the objects from the negotiator module
    >>> from negotiator import ContentNegotiator, AcceptParameters, ContentType, Language

    # Specify the default parameters.  These are the parameters which will be used in
    # place of any HTTP Accept headers which are not present in the negotiation request
    # For example, if the Accept-Language header is not passed to the negotiator
    # it will assume that the client request is for "en"
    >>> default_params = AcceptParameters(ContentType("text/html"), Language("en"))

    # Specify the list of acceptable formats that the server supports.  For this
    # advanced example we specify html, json and pdf in a variety of languages
    >>> acceptable = [AcceptParameters(ContentType("text/html"), Language("en"))]
    >>> acceptable.append(AcceptParameters(ContentType("text/html"), Language("fr")))
    >>> acceptable.append(AcceptParameters(ContentType("text/html"), Language("de")))
    >>> acceptable.append(AcceptParameters(ContentType("text/json"), Language("en")))
    >>> acceptable.append(AcceptParameters(ContentType("text/json"), Language("cz")))
    >>> acceptable.append(AcceptParameters(ContentType("application/pdf"), Language("de")))

    # specify the weighting that the negotiator should apply to the different
    # Accept headers.  A higher weighting towards content type will prefer content
    # type variations over language variations (e.g. if there are two formats
    # which are equally acceptable to the client, in different languages, a
    # content_type weight higher than a language weight will return the parameters
    # according to the server's preferred content type.
    >>> weights = {"content_type" : 1.0, "language" : 0.5}

    # Create an instance of the negotiator, ready to accept negotiation requests
    >>> cn = ContentNegotiator(default_params, acceptable, weights)

    # set up some more complex accept headers (you can try modifying the order
    # of the elements without q values, and the q values themselves, to see
    # different results).
    >>> accept = "text/html, text/json;q=1.0, application/pdf;q=0.5"
    >>> accept_language = "en;q=0.5, de, cz, fr"

    # negotiate over both headers, looking for an optimal solution to the client
    # request
    >>> acceptable = cn.negotiate(accept, accept_language)

    # The negotiator indicates the best fit to the client request is text/html
    # in german
    >>> acceptable
    AcceptParameters:: Content Type: text/html;Language: de;
    """
    def __init__(self, default_accept_parameters=None, acceptable=[], weights=None,
                 ignore_language_variants=False):
        """
        There are 4 parameters which must be set in order to start content negotiation
        - default_accept_parameters - the parameters to use when all or part of
            the analysed accept headers is not present
        - acceptable - What AcceptParameter objects are acceptable to
            return (in order of preference)
        - weights - the relative weights to apply to the different accept headers
        - ignore_language_variants - whether the content negotiator should ignore language
            variants overall
        """
        self.acceptable = acceptable
        self.default_accept_parameters = default_accept_parameters
        self.weights = weights if weights is not None else {
            'content_type': 1.0,
            'language': 1.0,
            'charset': 1.0,
            'encoding': 1.0,
            'packaging': 1.0}
        self.ignore_language_variants = ignore_language_variants

        if "content_type" not in self.weights:
            self.weights["content_type"] = 1.0
        if "language" not in self.weights:
            self.weights["language"] = 1.0
        if "charset" not in self.weights:
            self.weights["charset"] = 1.0
        if "encoding" not in self.weights:
            self.weights["encoding"] = 1.0
        if "packaging" not in self.weights:
            self.weights["packaging"] = 1.0

    def negotiate(self, accept=None, accept_language=None, accept_encoding=None,
                  accept_charset=None, accept_packaging=None):
        """
        Main method for carrying out content negotiation over the supplied HTTP headers.
        Returns either the preferred AcceptParameters as per the settings of the object, or
        None if no agreement could be reached.

        The arguments are the raw strings from the relevant HTTP headers

        - accept - HTTP Header: Accept; for example "text/html;q=1.0, text/plain;q=0.4"
        - accept_language - HTTP Header: Accept-Language; for example "en, de;q=0.8"
        - accept_encoding - HTTP Header: Accept-Encoding; not currently supported in negotiation
        - accept_charset - HTTP Header: Accept-Charset; not currently supported in negotiation
        - accept_packaging - HTTP Header: Accept-Packaging (from SWORD 2.0); a URI only, no
                             q values

        If verbose=True, then this will print to stdout
        """

        if (accept is None and accept_language is None and accept_encoding is None and
                accept_charset is None and accept_packaging is None):
            # if it is not available just return the defaults
            return self.default_accept_parameters

        log.info("Accept: " + str(accept))
        log.info("Accept-Language: " + str(accept_language))
        log.info("Accept-Packaging: " + str(accept_packaging))

        # get us back a dictionary keyed by q value which tells us the order of
        # preference that the client has requested
        accept_analysed = self._analyse_accept(accept)
        lang_analysed = self._analyse_language(accept_language)
        encoding_analysed = self._analyse_encoding(accept_encoding)
        charset_analysed = self._analyse_charset(accept_charset)
        packaging_analysed = self._analyse_packaging(accept_packaging)

        log.info("Accept Analysed: " + str(accept_analysed))
        log.info("Language Analysed: " + str(lang_analysed))
        log.info("Packaging Analysed: " + str(packaging_analysed))

        # now combine these results into one list of preferred accepts
        preferences = self._list_acceptable(
            self.weights, accept_analysed, lang_analysed, encoding_analysed,
            charset_analysed, packaging_analysed)

        log.info("Preference List: " + str(preferences))

        # go through the analysed formats and cross reference them with the acceptable formats
        accept_parameters = self._get_acceptable(preferences, self.acceptable)

        log.info("Acceptable: " + str(accept_parameters))

        # return the acceptable type.  If this is None (which get_acceptable can return),
        # then the caller will know that we failed to negotiate a type and should 415 the client
        return accept_parameters

    def _list_acceptable(self, weights, content_types=None, languages=None, encodings=None,
                         charsets=None, packaging=None):

        log.debug("Relative weights: " + str(weights))

        if content_types is None:
            content_types = {0.0: [None]}
        if languages is None:
            languages = {0.0: [None]}
        if encodings is None:
            encodings = {0.0: [None]}
        if charsets is None:
            charsets = {0.0: [None]}
        if packaging is None:
            packaging = {0.0: [None]}

        log.debug("Matrix of options:")
        log.debug("Content Types: " + str(content_types))
        log.debug("Languages: " + str(languages))
        log.debug("Encodings: " + str(encodings))
        log.debug("Charsets: " + str(charsets))
        log.debug("Packaging: " + str(packaging))

        unsorted = []

        # create an accept_parameter for each first precedence field
        # FIXME: this is hideous, but recursive programming is making my head
        # hurt so screw it.
        for q1, vals1 in content_types.items():
            for v1 in vals1:
                for q2, vals2 in languages.items():
                    for v2 in vals2:
                        for q3, vals3 in encodings.items():
                            for v3 in vals3:
                                for q4, vals4 in charsets.items():
                                    for v4 in vals4:
                                        for q5, vals5 in packaging.items():
                                            wq = ((weights['content_type'] * q1) + (weights['language'] * q2) +  # noqa
                                                    (weights['encoding'] * q3) + (weights['charset'] * q4) + # noqa
                                                    (weights['packaging'] * q5))
                                            for v5 in vals5:
                                                ap = AcceptParameters(v1, v2, v3, v4, v5)
                                                unsorted.append((ap, wq))
        return self._sort_by_q(unsorted, 0.0)

    def _analyse_packaging(self, accept):
        if accept is None:
            return None

        # if the header is not none, then it should be a straightforward uri,
        # with no q value, so our return is simple:
        return {1.0: [accept]}

    def _analyse_encoding(self, accept):
        return None

    def _analyse_charset(self, accept):
        return None

    def _analyse_language(self, accept):
        if accept is None:
            return None
        parts = self._split_accept_header(accept)
        highest_q = 0.0
        counter = 0
        unsorted = []
        for part in parts:
            counter += 1
            lang, sublang, q = self._interpret_accept_language_field(part, -1 * counter)
            if q > highest_q:
                highest_q = q
            unsorted.append((Language(language=lang, variant=sublang), q))
        sorted = self._sort_by_q(unsorted, highest_q)

        # now we have a dictionary keyed by q value which we can return
        return sorted

    def _analyse_accept(self, accept):
        """
        Analyse the Accept header string from the HTTP headers and return a structured
        dictionary with each content types grouped by their common q values, thus:

        dict = {
            1.0 : [<ContentType>, <ContentType>],
            0.8 : [<ContentType],
            0.5 : [<ContentType>, <ContentType>]
        }

        This method will guarantee that every content type has some q value associated
        with it, even if this was not supplied in the original Accept header; it will
        be inferred based on the rules of content negotiation
        """
        if accept is None:
            return None

        # the accept header is a list of content types and q values, in a comma separated list
        parts = self._split_accept_header(accept)

        # set up some registries for the coming analysis.  unsorted will hold each part
        # of the accept header following its analysis, but without respect to its position
        # in the preferences list.  highest_q and counter will be recorded during this
        # first run so that we can use them to sort the list later
        unsorted = []
        highest_q = 0.0
        counter = 0

        # go through each possible content type and analyse it along with its q value
        for part in parts:
            # count the part number that we are working on, starting from 1
            counter += 1

            type, params, q = self._interpret_accept_field(part, -1 * counter)
            supertype, subtype = type.split("/", 1)
            if q > highest_q:
                highest_q = q

            # at the end of the analysis we have all of the components with or without
            # their default values, so we just record the analysed version for the time
            # being as a tuple in the unsorted array
            unsorted.append((ContentType(type=supertype, subtype=subtype, params=params), q))

        # once we've finished the analysis we'll know what the highest explicitly requested
        # q will be.  This may leave us with a gap between 1.0 and the highest requested q,
        # into which we will want to put the content types which did not have explicitly
        # assigned q values.  Here we calculate the size of that gap, so that we can use it
        # later on in positioning those elements.  Note that the gap may be 0.0.
        sorted = self._sort_by_q(unsorted, highest_q)

        # now we have a dictionary keyed by q value which we can return
        return sorted

    def _sort_by_q(self, unsorted, q_max):
        # set up a dictionary to hold our sorted results.  The dictionary will be keyed
        # with the q value, and the value of each key will be an array of ContentType
        # objects (in no particular order)
        sorted = {}

        # go through the unsorted list
        for (value, q) in unsorted:
            if q > 0:
                # if the q value is greater than 0 it was explicitly assigned in the
                # Accept header and we can just place it into the sorted dictionary
                self.insert(sorted, q, value)
            else:
                # otherwise, we have to calculate the q value using the following equation
                # which creates a q value "qv" within "q_range" of 1.0 [the first part of
                # the eqn] based on the fraction of the way through the total
                # accept header list scaled by the q_range [the second part of the eqn]
                # qv = (1.0 - q_range) + (((-1 * q)/scale_factor) * q_range)

                # this is the fraction of the remaining spare q values that we can assign
                q_fraction = 1.0 / (-1.0 * q)
                # this scales the fraction to the remaining q range and adds it onto the
                # highest other qs (this also handles q_max = 1.0 implicitly)
                qv = q_max + ((1.0 - q_max) * q_fraction)
                self.insert(sorted, qv, value)

        # now we have a dictionary keyed by q value which we can return
        return sorted

    def _split_accept_header(self, accept):
        return [a.strip() for a in accept.split(",")]

    def _interpret_accept_language_field(self, accept, default_q):
        components = accept.split(";")

        lang = None
        sublang = None
        q = default_q

        # the first part can be a language, or a language-sublanguage pair (like en, or en-gb)
        langs = components[0].strip()
        lang_parts = langs.split("-")
        if len(lang_parts) == 1:
            lang = lang_parts[0]
        elif len(lang_parts) == 2:
            lang = lang_parts[0]
            sublang = lang_parts[1]

        if len(components) == 2:
            # strip the "q=" from the start of the q value
            q = components[1].strip()[2:]

        return (lang, sublang, float(q))

    def _interpret_accept_field(self, accept, default_q):

        # the components of the part can be "type;params;q" "type;params", "type;q" or just "type"
        components = accept.split(";")

        # the first part is always the type (see above comment)
        type = components[0].strip()

        # create some default values for the other parts.  If there is no params, we
        # will use None, if there is no q we will use a negative number multiplied
        # by the position in the list of this part.  This allows us to later see the
        # order in which the parts with no q value were listed, which is important
        params = None
        q = default_q

        # There are then 3 possibilities remaining to check for: "type;q",
        # "type;params" and "type;params;q"
        # ("type" is already handled by the default cases set up above)
        if len(components) == 2:
            # "type;q" or "type;params"
            if components[1].strip().startswith("q="):
                # "type;q"
                # strip the "q=" from the start of the q value
                q = components[1].strip()[2:]
            else:
                # "type;params"
                params = components[1].strip()
        elif len(components) == 3:
            # "type;params;q"
            # strip the "q=" from the start of the q value
            params = components[1].strip()
            q = components[2].strip()[2:]

        return (type, params, float(q))

    def insert(self, d, q, v):
        """
        Utility method: if dict d contains key q, then append value v to the array which
        is identified by that key otherwise create a new key with the value of an array
        with a single value v
        """
        if q in d:
            d[q].append(v)
        else:
            d[q] = [v]

    def _contains_match(self, source, target):
        """
        Does the target list of AcceptParameters objects contain a match for the supplied source
        Args:
        - source: An AcceptParameters object which we want to see if it matches anything in the
                  target
        - target: A list of AcceptParameters objects to try to match the source against
        Returns the matching AcceptParameters from the target list, or None if no such match
        """
        for ap in target:
            if source.matches(ap, ignore_language_variants=self.ignore_language_variants):
                # matches are symmetrical, so source.matches(ap) == ap.matches(source) so
                # way round is irrelevant we return the target's content type, as this is
                # considered the definitive list of allowed content types, while the
                # source may contain wildcards
                return ap
        return None

    def _get_acceptable(self, client, server):
        """
        Take the client content negotiation requirements and the server's
        array of supported types (in order of preference) and determine the most
        acceptable format to return.

        This method always returns the client's most preferred format if the server
        supports it, irrespective of the server's preference.  If the client has no
        discernable preference between two formats (i.e. they have the same
        q value) then the server's preference is taken into account.

        Returns an AcceptParameters object represening the mutually acceptable content
        type, or None if no agreement could be reached.
        """
        log.info("Client: " + str(client))
        log.info("Server: " + str(server))

        # get the client requirement keys sorted with the highest q first (the
        # server is a list which should be in order of preference already)
        ckeys = client.keys()
        sorted(ckeys, reverse=True)

        # the rule for determining what to return is that "the client's preference
        # always wins", so we look for the highest q ranked item that the server is
        # capable of returning.  We only take into account the server's preference
        # when the client has two equally weighted preferences - in that case we
        # take the server's preferred content type
        for q in ckeys:
            # for each q in order starting at the highest
            possibilities = client[q]
            allowable = []
            for p in possibilities:
                # for each accept parameter with the same q value

                # find out if the possibility p matches anything in the server.  This uses
                # the AcceptParameter's matches() method which will take into account
                # wildcards, so content types like */* will match appropriately.  We ge
                # back from this the concrete AcceptParameter as specified by the server
                # if there is a match, so we know the result contains no unintentional wildcards
                match = self._contains_match(p, server)
                if match is not None:
                    # if there is a match, register it
                    allowable.append(match)

            log.info("Allowable: " + str(q) + ":" + str(allowable))

            # we now know if there are 0, 1 or many allowable content types at this q value
            if len(allowable) == 0:
                # we didn't find anything, so keep looking at the next q value
                continue
            elif len(allowable) == 1:
                # we found exactly one match, so this is our content type to use
                return allowable[0]
            else:
                # we found multiple supported content types at this q value, so now we need
                # to choose the server's preference
                for i in range(len(server)):
                    # iterate through the server explicitly by numerical position
                    if server[i] in allowable:
                        # when we find our first content type in the allowable list, it is
                        # the highest ranked server content type that is allowable, so
                        # this is our type
                        return server[i]

        # we've got to here without returning anything, which means that the client and
        # server can't come to an agreement on what content type they want and can deliver.
        # There's nothing more we can do!
        return None


@implementer(IContentNegotiation)
class ContentNegotiatorUtility(object):

    def __init__(self, header, enabled_values):
        if header == 'content_type':
            server = [AcceptParameters(content_type=ContentType(x)) for x in enabled_values]
            self.cn = ContentNegotiator(acceptable=server)
        if header == 'language':
            server = [AcceptParameters(language=Language(x)) for x in enabled_values]
            self.cn = ContentNegotiator(acceptable=server)

    def negotiate(self, **kwargs):
        return self.cn.negotiate(**kwargs)


def content_type_negotiation(request, resource, view):
    # We need to check for the language

    accept = None

    if 'ACCEPT' in request.headers:
        accept = request.headers['ACCEPT']

    if IDownloadView.providedBy(view) or accept in (None, '*/*'):
        # if download view, we want to render raw immediately
        # or if no or */* accept header provided
        return IRendererFormatRaw

    np = get_utility(IContentNegotiation, 'content_type')
    ap = np.negotiate(accept=accept)
    # We need to check for the accept
    if str(ap.content_type) in app_settings['renderers']:
        return app_settings['renderers'][str(ap.content_type)]
    else:
        log.info('Could not find content type {} renderer'.format(
            str(ap.content_type)))
        return IRendererFormatRaw


def language_negotiation(request):
    # We need to check for the language

    if 'ACCEPT-LANGUAGE' in request.headers:
        accept_lang = request.headers['ACCEPT-LANGUAGE']
    else:
        accept_lang = 'en'

    np = get_utility(IContentNegotiation, 'language')
    ap = np.negotiate(accept_language=accept_lang)
    # We need to check for the accept
    if ap is None:
        language = app_settings['languages']['en']
    else:
        if str(ap.language) in app_settings['languages']:
            language = app_settings['languages'][str(ap.language)]
        else:
            language = app_settings['languages']['en']
    return language
