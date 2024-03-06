
from __future__ import print_function, division

import os
import json 
import bisect

def from_base64_vlq(value):
    BASE64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    return BASE64_CHARS.index(value)

def decode_vlq(encoded):
    shift = 0
    result = 0
    continuation = False
    decoded_values = []

    for char in encoded:
        # Convert base64 character to a value
        value = from_base64_vlq(char)

        # Check if the continuation bit is set
        continuation = value & 0x20
        # Obtain the next 5 bits of the value
        value &= 0x1F
        result += value << shift
        shift += 5

        if not continuation:
            # If the result is negative, perform the necessary conversion
            if result & 1:
                result = -(result >> 1)
            else:
                result = result >> 1
            # Append the result to the list of decoded values
            decoded_values.append(result)
            # Reset variables for the next value
            result = 0
            shift = 0

    if continuation:
        raise ValueError("Incomplete VLQ sequence")

    return decoded_values


class SingleMap:
    """ represents a single js map file
    """

    def __init__(self, js_map):
        self._map_path = "sourcemap.d/%s" % js_map

    def _parseMapping(self, sm):
        groups = sm['mappings'].split(';')

        out = []
        for grp in groups:
            ids = [0] * 5
            lns = []
            
            segments = grp.split(',')
            for seg in segments:
                d = decode_vlq(seg)
                d += [None] * (5 - len(d))     # extents
                if d[0] is not None: ids[0] += d[0]
                if d[1] is not None: ids[1] += d[1]
                if d[2] is not None: ids[2] += d[2]
                if d[3] is not None: ids[3] += d[3]
                if d[4] is not None: ids[4] += d[4]
                
                #name = sm['names'][ids[4]] if d[4] is not None else ''
                #print(seg, d, ids, name)
                lns.append([ids[0], ids[1], ids[2], ids[3], ids[4]])
            out.append(lns)
        return out

    def _parse(self, sm):
        # replace mappings
        sm['mappings'] = self._parseMapping(sm)
       
        out = []
        for grp in sm['mappings']:
            out.append([ x[0] for x in grp ])
        sm['indexes'] = out
        return sm

    def Load(self):
        with open(self._map_path, 'r') as f:
            sm = json.load(f)
            self._raw = self._parse(sm)
            #print(self._raw['indexes'][0])
        return True 

    def GetOriginalPositionFor(self, line, column):
        sm = self._raw
        if line > len(sm['mappings']):
            return None
        index = bisect.bisect_left(sm['indexes'][line], column)
        if index is None:
            return None
        d = sm['mappings'][line][index]
     
        # map_column, file, line, column, name
        source = sm['sources'][d[1]]
        line = d[2]
        column = d[3]
        name = sm['names'][d[4]] if d[4] is not None else ''
        return (source, line, column, name)

class SourceMaps:
    """ represents auto loaded all js map files.
    """

    _source_maps = {}

    @classmethod
    def Load(cls):
        if not os.path.exists('sourcemap.d'):
            return 

        # load all js.map files in sourcemap.d
        for filename in os.listdir('sourcemap.d'):
            if filename.endswith('.js.map'):
                jsmap = SingleMap(filename)
                if jsmap.Load():
                    cls._source_maps[filename] = jsmap
                    print("sourcemap '%s' loaded." % filename)
       
        # debug only don't commit
        #print(cls.GetOriginalPositionFor('vendor.cjs.es5.production.js.map', 0, 11757))
   
    @classmethod
    def GetOriginalPositionFor(cls, js_map, line, column):
        assert isinstance(js_map, str)

        #for i in cls._source_maps.keys():
        #    print(i, js_map, i.strip() == js_map.strip())
        if js_map not in cls._source_maps:
            return None

        return cls._source_maps[js_map].GetOriginalPositionFor(line, column)

