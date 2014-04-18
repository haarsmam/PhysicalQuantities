# -*- coding: utf-8 -*-

import numpy as np
from math import pi

from NDict import *

class UnitError(ValueError):
    pass

# Helper functions
def findUnit(unit):
    if isinstance(unit, basestring):
        name = unit.strip().replace('^', '**').replace('µ', 'mu').replace('°', 'deg')
        try:
            unit = eval(name, unit_table)
        except NameError:
            raise UnitError('Invalid or unknown unit in %s' % name)
        for cruft in ['__builtins__', '__args__']:
            try:
                del unit_table[cruft]
            except:
                pass
    if not isPhysicalUnit(unit):
        raise UnitError(str(unit) + ' is not a unit')
    return unit


def convertValue(value, src_unit, target_unit):
    (factor, offset) = src_unit.conversion_tuple_to(target_unit)
    if isinstance(value, list):
        raise UnitError('Cannot convert units for a list')
    return (value + offset) * factor


def isPhysicalUnit(x):
    return hasattr(x, 'factor') and hasattr(x, 'powers')

class PhysicalUnit(object):
    """Physical unit.

    A physical unit is defined by a name (possibly composite), a scaling factor,
    and the exponentials of each of the SI base units that enter into it. Units
    can be multiplied, divided, and raised to integer powers.
    """

    def __init__(self, names, factor, powers, offset=0,url='',comment=''):
        """
        @param names: a dictionary mapping each name component to its
                      associated integer power (e.g. C{{'m': 1, 's': -1}})
                      for M{m/s}). As a shorthand, a string may be passed
                      which is assigned an implicit power 1.
        @param factor: a scaling factor
        @param powers: the integer powers for each of the nine base units
        @param offset: an additive offset to the base unit (used only for
                       temperatures)
        """

        self.prefixed = False
        self.baseunit = self
        self.comment = comment
        self.url = url        
        if isinstance(names, basestring):
            self.names = NumberDict()
            self.names[names] = 1
        else:
            self.names = names
        self.factor = factor
        self.offset = offset
        self.powers = powers

    def set_name(self, name):
        self.names = NumberDict()
        self.names[name] = 1

    @property
    def name(self):
        num = ''
        denom = ''
        for unit in self.names.keys():
            power = self.names[unit]
            if power < 0:
                denom = denom + '/' + unit
                if power < -1:
                    denom = denom + '**' + str(-power)
            elif power > 0:
                num = num + '*' + unit
                if power > 1:
                    num = num + '**' + str(power)
        if len(num) == 0:
            num = '1'
        else:
            num = num[1:]
        return num + denom

    @property
    def is_dimensionless(self):
        return not reduce(lambda a, b: a or b, self.powers)

    @property
    def is_angle(self):
        return self.powers[7] == 1 and \
            reduce(lambda a, b: a + b, self.powers) == 1

    def __str__(self):
        name = self.name.strip().replace('**', r'^').replace('mu', r'µ').replace('deg', r'°')
        return name

    def __repr__(self):
        return '<PhysicalUnit ' + self.name + '>'

    def _repr_latex_(self): 
        """ Return latex representation of unit
            TODO: more info for aggregate units 
        """
        unit = self.name.replace('**', '^').replace('mu', 'µ').replace('deg', '°').replace('*', r' \cdot ').replace(' pi', r' \pi ')
        if self.prefixed == False:
            if self.comment is not '':
                info = '(<a href="' + self.url + '" target="_blank">'+ self.comment + '</a>)'
            else:
                info = ''
        else:
            baseunit = self.baseunit
            if baseunit.comment == '':
                info = r'$ = %s \cdot %s$ ' % (self.factor, self.baseunit)            
            else:
                info = r'$ = %s \cdot %s$ (' % (self.factor, self.baseunit) +\
                    '<a href="' + baseunit.url + '" target="_blank">'+ baseunit.comment + '</a>)'            
        s = r'$%s$ %s' % (unit, info)
        return s

    @property
    def latex(self):
        return Latex(self._repr_latex_())

    def __cmp__(self, other):
        if self.powers != other.powers:
            raise UnitError('Incompatible units')
        return cmp(self.factor, other.factor)

    def __mul__(self, other):
        if self.offset != 0 or (isPhysicalUnit(other) and other.offset != 0):
            raise UnitError('Cannot multiply units with non-zero offset')
        if isPhysicalUnit(other):
            return PhysicalUnit(self.names + other.names,
                                self.factor * other.factor,
                                map(lambda a, b: a+b, self.powers, other.powers))
        else:
            return PhysicalUnit(self.names + {str(other): 1},
                                self.factor * other, self.powers,
                                self.offset * other)

    __rmul__ = __mul__

    def __div__(self, other):
        if self.offset != 0 or (isPhysicalUnit(other) and other.offset != 0):
            raise UnitError('Cannot divide units with non-zero offset')
        if isPhysicalUnit(other):
            return PhysicalUnit(self.names - other.names,
                                self.factor / other.factor,
                                map(lambda a, b: a-b, self.powers, other.powers))
        else:
            return PhysicalUnit(self.names+{str(other): -1},
                                self.factor/other, self.powers)

    def __rdiv__(self, other):
        if self.offset != 0 or (isPhysicalUnit(other) and other.offset != 0):
            raise UnitError('Cannot divide units with non-zero offset')
        if isPhysicalUnit(other):
            return PhysicalUnit(other.names - self.names,
                                other.factor/self.factor,
                                map(lambda a, b: a-b, other.powers, self.powers))
        else:
            return PhysicalUnit({str(other): 1} - self.names,
                                other / self.factor,
                                map(lambda x: -x, self.powers))

    def __pow__(self, other):
        if self.offset != 0:
            raise UnitError('Cannot exponentiate units with non-zero offset')
        if isinstance(other, int):
            return PhysicalUnit(other*self.names, pow(self.factor, other),
                                map(lambda x, p=other: x*p, self.powers))
        if isinstance(other, float):
            inv_exp = 1./other
            rounded = int(np.floor(inv_exp + 0.5))
            if abs(inv_exp-rounded) < 1.e-10:
                if reduce(lambda a, b: a and b,
                          map(lambda x, e=rounded: x%e == 0, self.powers)):
                    f = pow(self.factor, other)
                    p = map(lambda x, p=rounded: x/p, self.powers)
                    if reduce(lambda a, b: a and b,
                              map(lambda x, e=rounded: x%e == 0,
                                  self.names.values())):
                        names = self.names/rounded
                    else:
                        names = NumberDict()
                        if f != 1.:
                            names[str(f)] = 1
                        for i in range(len(p)):
                            names[base_names[i]] = p[i]
                    return PhysicalUnit(names, f, p)
                else:
                    raise UnitError('Illegal exponent %f' % other)
        raise UnitError('Only integer and inverse integer exponents allowed')

    def conversion_factor_to(self, other):
        """Return conversion factor to another unit."""
        if self.powers != other.powers:
            raise UnitError('Incompatible units')
        if self.offset != other.offset and self.factor != other.factor:
            raise UnitError(('Unit conversion (%s to %s) cannot be expressed ' +
                            'as a simple multiplicative factor') %
                            (self.name, other.name))
        return self.factor/other.factor

    def conversion_tuple_to(self, other):
        """Return conversion factor and offset to another unit."""
        if self.powers != other.powers:
            raise UnitError('Incompatible units')

        # let (s1,d1) be the conversion tuple from 'self' to base units
        #   (ie. (x+d1)*s1 converts a value x from 'self' to base units,
        #   and (x/s1)-d1 converts x from base to 'self' units)
        # and (s2,d2) be the conversion tuple from 'other' to base units
        # then we want to compute the conversion tuple (S,D) from
        #   'self' to 'other' such that (x+D)*S converts x from 'self'
        #   units to 'other' units
        # the formula to convert x from 'self' to 'other' units via the
        #   base units is (by definition of the conversion tuples):
        #     ( ((x+d1)*s1) / s2 ) - d2
        #   = ( (x+d1) * s1/s2) - d2
        #   = ( (x+d1) * s1/s2 ) - (d2*s2/s1) * s1/s2
        #   = ( (x+d1) - (d1*s2/s1) ) * s1/s2
        #   = (x + d1 - d2*s2/s1) * s1/s2
        # thus, D = d1 - d2*s2/s1 and S = s1/s2
        factor = self.factor / other.factor
        offset = self.offset - (other.offset * other.factor / self.factor)
        return (factor, offset)

    def html_list(self):
        """ List all defined units """
        from IPython.display import display, Math, Latex, HTML
        str = "<table>"
        str += "<tr><th>Name</th><th>Base Unit</th><th>Quantity</th></tr>"
        for name in unit_table:
            unit = unit_table[name]
            if isinstance(unit,PhysicalUnit):
                if unit.prefixed == False:
                    if isinstance(unit.baseunit, PhysicalUnit):
                        baseunit = '$ %s $' % unit.baseunit
                    else:
                        baseunit = '$ %s $' % unit.baseunit.replace('**', '^').replace('mu', 'µ').replace('deg', '°').replace('*', r' \cdot ').replace('pi', r' \pi ')
                    #baseunit = '$ %s $' % unit.baseunit 
                    #print baseunit
                    #baseunit = str(unit.baseunit)
                    #replace(' pi', r' \pi ')
                    str+= "<tr><td>" + unit.name + '</td><td>' + baseunit +\
                          '</td><td><a href="' + unit.url+'" target="_blank">'+ unit.comment +\
                          "</a></td></tr>"
        str += "</table>"
        return HTML(str)
        
    def list(self):
        """ List all defined units """
        str=[]
        for name in unit_table:
            unit = unit_table[name]
            if isinstance(unit,PhysicalUnit) and unit.prefixed == False:
                str.append(unit.name)
        return str


def addUnit(name, unit, comment='',prefixed=False, baseunit=None, url=''):
    """ Add new PhysicalUnit entry """
    if name in unit_table:
        raise KeyError('Unit ' + name + ' already defined')
    if isinstance(unit, str):
        newunit = eval(unit, unit_table)
        for cruft in ['__builtins__', '__args__']:
            try:
                del unit_table[cruft]
            except:
                pass
    else:
        newunit = unit
    newunit.set_name(name)
    newunit.comment = comment
    if prefixed == True:
        newunit.baseunit = baseunit
    else:
        newunit.baseunit = unit
    newunit.prefixed = prefixed
    newunit.url = url
    unit_table[name] = newunit
    return name


def addPrefixed(unitname, range='full'):
    """ Add prefixes to already defined unit 
        unitname: name of unit to be prefixed
                  e.k. 'm' -> 'mm','cm','dm','km'...
        range: 'engineering' -> 1e-18 to 1e12
               'full' -> 1e-24 to 1e24
    """
    if range =='engineering':
        _prefixes = _engineering_prefixes
    else:
        _prefixes = _full_prefixes
    unit = unit_table[unitname]
    for prefix in _prefixes:
        prefixedname = prefix[0] + unitname
        if prefixedname not in unit_table:
            addUnit(prefixedname, prefix[1]*unit,prefixed=True,baseunit=unit)


# add scaling prefixes
_full_prefixes = [
    ('Y',  1.e24), ('Z',  1.e21), ('E',  1.e18), ('P',  1.e15), ('T',  1.e12),
    ('G',  1.e9),  ('M',  1.e6),  ('k',  1.e3),  ('h',  1.e2),  ('da', 1.e1),
    ('d',  1.e-1), ('c',  1.e-2), ('m',  1.e-3), ('mu', 1.e-6), ('n',  1.e-9),
    ('p',  1.e-12), ('f',  1.e-15), ('a',  1.e-18), ('z',  1.e-21),
    ('y',  1.e-24),
]

# actually, use a reduced set of scaling prefixes is enough for engineering
# purposes:
_engineering_prefixes = [
    ('T',  1.e12),
    ('G',  1.e9),  ('M',  1.e6),  ('k',  1.e3),  ('h',  1.e2),  ('da', 1.e1),
    ('d',  1.e-1), ('c',  1.e-2), ('m',  1.e-3), ('mu', 1.e-6), ('n',  1.e-9),
    ('p',  1.e-12), ('f',  1.e-15), ('a',  1.e-18),
]

unit_table = {}
# These are predefined base units 
base_names = ['m', 'kg', 's', 'A', 'K', 'mol', 'cd', 'rad', 'sr']

addUnit('kg', PhysicalUnit('kg', 1,     [0, 1, 0, 0, 0, 0, 0, 0, 0],url='https://en.wikipedia.org/wiki/Kilogram', comment='Kilogram'))
addPrefixed(addUnit('m', PhysicalUnit('m',   1.,    [1, 0, 0, 0, 0, 0, 0, 0, 0],url='https://en.wikipedia.org/wiki/Metre', comment='Metre')),range='engineering')
addPrefixed(addUnit('g', PhysicalUnit('g',   0.001, [0, 1, 0, 0, 0, 0, 0, 0, 0],url='https://en.wikipedia.org/wiki/Kilogram', comment='Kilogram')),range='engineering')
addPrefixed(addUnit('s', PhysicalUnit('s',   1.,    [0, 0, 1, 0, 0, 0, 0, 0, 0],url='https://en.wikipedia.org/wiki/Second', comment='Second')),range='engineering')
addPrefixed(addUnit('A', PhysicalUnit('A',   1.,    [0, 0, 0, 1, 0, 0, 0, 0, 0],url='https://en.wikipedia.org/wiki/Ampere', comment='Ampere')),range='engineering')
addPrefixed(addUnit('K', PhysicalUnit('K',   1.,    [0, 0, 0, 0, 1, 0, 0, 0, 0],url='https://en.wikipedia.org/wiki/Kelvin', comment='Kelvin')),range='engineering')
addPrefixed(addUnit('mol', PhysicalUnit('mol', 1.,    [0, 0, 0, 0, 0, 1, 0, 0, 0],url='https://en.wikipedia.org/wiki/Mole_(unit)', comment='Mol')),range='engineering')
addPrefixed(addUnit('cd', PhysicalUnit('cd',  1.,    [0, 0, 0, 0, 0, 0, 1, 0, 0],url='https://en.wikipedia.org/wiki/Candela', comment='Candela')),range='engineering')
addPrefixed(addUnit('rad', PhysicalUnit('rad', 1.,    [0, 0, 0, 0, 0, 0, 0, 1, 0],url='https://en.wikipedia.org/wiki/Radian', comment='Radian')),range='engineering')
addPrefixed(addUnit('sr', PhysicalUnit('sr',  1.,    [0, 0, 0, 0, 0, 0, 0, 0, 1],url='https://en.wikipedia.org/wiki/Steradian', comment='Streradian')),range='engineering')
addPrefixed(addUnit('Hz', '1/s', 'Hertz', url='https://en.wikipedia.org/wiki/Hertz'),range='engineering')
addPrefixed(addUnit('N', 'm*kg/s**2', 'Newton', url='https://en.wikipedia.org/wiki/Newton_(unit)'),range='engineering')
addPrefixed(addUnit('Pa', 'N/m**2', 'Pascal', url='https://en.wikipedia.org/wiki/Pascal_(unit)'),range='engineering')
addPrefixed(addUnit('J', 'N*m', 'Joule', url='https://en.wikipedia.org/wiki/Joule'),range='engineering')
addPrefixed(addUnit('W', 'J/s', 'Watt', url='https://en.wikipedia.org/wiki/Watt'),range='engineering')
addPrefixed(addUnit('C', 's*A', 'Coulomb', url='https://en.wikipedia.org/wiki/Coulomb'),range='engineering')
addPrefixed(addUnit('V', 'W/A', 'Volt', url='https://en.wikipedia.org/wiki/Volt'),range='engineering')
addPrefixed(addUnit('F', 'C/V', 'Farad', url='https://en.wikipedia.org/wiki/Farad'),range='engineering')
addPrefixed(addUnit('Ohm', 'V/A', 'Ohm', url='https://en.wikipedia.org/wiki/Ohm_(unit)'),range='engineering')
addPrefixed(addUnit('S', 'A/V', 'Siemens', url='https://en.wikipedia.org/wiki/Siemens_(unit)'),range='engineering')
addPrefixed(addUnit('Wb', 'V*s', 'Weber', url='https://en.wikipedia.org/wiki/Weber_(unit)'),range='engineering')
addPrefixed(addUnit('T', 'Wb/m**2', 'Tesla', url='https://en.wikipedia.org/wiki/Tesla_(unit)'),range='engineering')
addPrefixed(addUnit('H', 'Wb/A', 'Henry', url='https://en.wikipedia.org/wiki/Henry_(unit)'),range='engineering')
addPrefixed(addUnit('lm', 'cd*sr', 'Lumen', url='https://en.wikipedia.org/wiki/Lumen_(unit)'),range='engineering')
addPrefixed(addUnit('lx', 'lm/m**2', 'Lux', url='https://en.wikipedia.org/wiki/Lux'),range='engineering')

# Angle units
unit_table['pi'] = pi #np.pi
addUnit('deg', 'pi*rad/180', 'Degree', url='http://en.wikipedia.org/wiki/Degree_%28angle%29')
addUnit('arcmin', 'pi*rad/180/60', 'minutes of arc')
addUnit('arcsec', 'pi*rad/180/3600', 'seconds of arc')

addUnit('min', '60*s', 'Minute', url='https://en.wikipedia.org/wiki/Hour')
addUnit('h', '60*60*s', 'Hour', url='https://en.wikipedia.org/wiki/Hour')

