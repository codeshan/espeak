#!/usr/bin/python

# Copyright (C) 2012, 2014 Reece H. Dunn
#
# This file is part of ucd-tools.
#
# ucd-tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ucd-tools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ucd-tools.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import ucd

ucd_rootdir = sys.argv[1]
ucd_version = sys.argv[2]

unicode_chars = {}
for data in ucd.parse_ucd_data(ucd_rootdir, 'UnicodeData'):
	for codepoint in data['CodePoint']:
		unicode_chars[codepoint] = data['GeneralCategory']
if '--with-csur' in sys.argv:
	for csur in ['Klingon']:
		for data in ucd.parse_ucd_data('data/csur', csur):
			for codepoint in data['CodePoint']:
				unicode_chars[codepoint] = data['GeneralCategory']

# This map is a combination of the information in the UnicodeData and Blocks
# data files. It is intended to reduce the number of character tables that
# need to be generated.
category_sets = [
	(ucd.CodeRange('000000..00D7FF'), None, 'Multiple Blocks'),
	(ucd.CodeRange('00D800..00DFFF'), 'Cs', 'Surrogates'),
	(ucd.CodeRange('00E000..00F7FF'), 'Co', 'Private Use Area'),
	(ucd.CodeRange('00F800..02FAFF'), None, 'Multiple Blocks'),
	(ucd.CodeRange('02FB00..0DFFFF'), 'Cn', 'Unassigned'),
	(ucd.CodeRange('0E0000..0E01FF'), None, 'Multiple Blocks'),
	(ucd.CodeRange('0E0200..0EFFFF'), 'Cn', 'Unassigned'),
	(ucd.CodeRange('0F0000..0FFFFD'), 'Co', 'Plane 15 Private Use'),
	(ucd.CodeRange('0FFFFE..0FFFFF'), 'Cn', 'Plane 15 Private Use'),
	(ucd.CodeRange('100000..10FFFD'), 'Co', 'Plane 16 Private Use'),
	(ucd.CodeRange('10FFFE..10FFFF'), 'Cn', 'Plane 16 Private Use'),
]

# These categories have many pages consisting of just this category:
#     Cn -- Unassigned
#     Lo -- CJK Ideographs
special_categories = ['Cn', 'Co', 'Lo', 'Sm', 'So']

category_tables = {}
for codepoints, category, comment in category_sets:
	if not category:
		table = {}
		table_entry = None
		table_codepoint = None
		table_category = None
		for i, codepoint in enumerate(codepoints):
			try:
				category = unicode_chars[codepoint]
			except KeyError:
				category = 'Cn' # Unassigned
			if (i % 256) == 0:
				if table_entry:
					if table_category in special_categories:
						table[table_codepoint] = table_category
					elif table_category:
						raise Exception('%s only table not in the special_categories list.' % table_category)
					else:
						table[table_codepoint] = table_entry
				table_entry = []
				table_codepoint = codepoint
				table_category = category
			if category != table_category:
				table_category = None
			table_entry.append(category)
		if table_entry:
			if table_category in special_categories:
				table[table_codepoint] = table_category
			else:
				table[table_codepoint] = table_entry
		category_tables['%s_%s' % (codepoints.first, codepoints.last)] = table

if __name__ == '__main__':
	sys.stdout.write("""/* Unicode General Categories
 *
 * Copyright (C) 2012 Reece H. Dunn
 *
 * This file is part of ucd-tools.
 *
 * ucd-tools is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * ucd-tools is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with ucd-tools.  If not, see <http://www.gnu.org/licenses/>.
 */

// NOTE: This file is automatically generated from the UnicodeData.txt file in
// the Unicode Character database by the ucd-tools/tools/categories.py script.

#include "ucd/ucd.h"

#include <stddef.h>

using namespace ucd;

// Unicode Character Data %s
""" % ucd_version)

	for category in special_categories:
		sys.stdout.write('\n')
		sys.stdout.write('static const uint8_t categories_%s[256] =\n' % category)
		sys.stdout.write('{')
		for i in range(0, 256):
			if (i % 16) == 0:
				sys.stdout.write('\n\t/* %02X */' % i)
			sys.stdout.write(' %s,' % category)
		sys.stdout.write('\n};\n')

	for codepoints, category, comment in category_sets:
		if not category:
			tables = category_tables['%s_%s' % (codepoints.first, codepoints.last)]
			for codepoint in sorted(tables.keys()):
				table = tables[codepoint]
				if table in special_categories:
					continue

				sys.stdout.write('\n')
				sys.stdout.write('static const uint8_t categories_%s[256] =\n' % codepoint)
				sys.stdout.write('{')
				for i, category in enumerate(table):
					if (i % 16) == 0:
						sys.stdout.write('\n\t/* %02X */' % i)
					sys.stdout.write(' %s,' % category)
				sys.stdout.write('\n};\n')

	for codepoints, category, comment in category_sets:
		if not category:
			table_index = '%s_%s' % (codepoints.first, codepoints.last)
			sys.stdout.write('\n')
			sys.stdout.write('static const uint8_t *categories_%s[] =\n' % table_index)
			sys.stdout.write('{\n')
			for codepoint, table in sorted(category_tables[table_index].items()):
				if isinstance(table, str):
					sys.stdout.write('\tcategories_%s, // %s\n' % (table, codepoint))
				else:
					sys.stdout.write('\tcategories_%s,\n' % codepoint)
			sys.stdout.write('};\n')

	sys.stdout.write('\n')
	sys.stdout.write('ucd::category ucd::lookup_category(codepoint_t c)\n')
	sys.stdout.write('{\n')
	for codepoints, category, comment in category_sets:
		if category:
			sys.stdout.write('\tif (c <= 0x%s) return %s; // %s : %s\n' % (codepoints.last, category, codepoints, comment))
		else:
			sys.stdout.write('\tif (c <= 0x%s) // %s\n' % (codepoints.last, codepoints))
			sys.stdout.write('\t{\n')
			sys.stdout.write('\t\tconst uint8_t *table = categories_%s_%s[(c - 0x%s) / 256];\n' % (codepoints.first, codepoints.last, codepoints.first))
			sys.stdout.write('\t\treturn (ucd::category)table[c % 256];\n')
			sys.stdout.write('\t}\n')
	sys.stdout.write('\treturn Ii; // Invalid Unicode Codepoint\n')
	sys.stdout.write('}\n')

	sys.stdout.write("""
ucd::category_group ucd::lookup_category_group(category c)
{
	switch (c)
	{
	case Cc: case Cf: case Cn: case Co: case Cs:
		return C;
	case Ll: case Lm: case Lo: case Lt: case Lu:
		return L;
	case Mc: case Me: case Mn:
		return M;
	case Nd: case Nl: case No:
		return N;
	case Pc: case Pd: case Pe: case Pf: case Pi: case Po: case Ps:
		return P;
	case Sc: case Sk: case Sm: case So:
		return S;
	case Zl: case Zp: case Zs:
		return Z;
	case Ii:
		return I;
	}
}

ucd::category_group ucd::lookup_category_group(codepoint_t c)
{
	return lookup_category_group(lookup_category(c));
}
""")
